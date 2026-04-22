import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class FundService:
    """基金数据服务类 - 使用天天基金网接口"""

    _fund_list_cache: Optional[List[Dict[str, str]]] = None
    _fund_list_cache_time: Optional[datetime] = None

    @staticmethod
    def _parse_js_var(text: str, var_name: str) -> Any:
        """从 JS 文本中解析变量值"""
        pattern = rf'var\s+{re.escape(var_name)}\s*=\s*(.+?);\s*(?:/\*|var\s+|$)'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            # 尝试更宽松的模式
            pattern2 = rf'{re.escape(var_name)}\s*=\s*(.+?);'
            match = re.search(pattern2, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def get_fund_list(keyword: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取基金列表（带缓存，1小时）
        limit: 返回数量限制，None 表示不限制（返回全市场）
        """
        try:
            # 检查缓存
            if FundService._fund_list_cache is not None:
                if FundService._fund_list_cache_time and \
                   (datetime.now() - FundService._fund_list_cache_time).seconds < 3600:
                    result = FundService._fund_list_cache
                    if keyword:
                        kw = keyword.lower()
                        result = [f for f in result if kw in f["code"].lower() or kw in f["name"].lower()]
                    return result[:limit] if limit else result

            url = "http://fund.eastmoney.com/js/fundcode_search.js"
            resp = requests.get(url, timeout=15)
            resp.encoding = "utf-8"
            text = resp.text

            data = FundService._parse_js_var(text, "r")
            if data is None:
                return []

            result = []
            for item in data:
                if len(item) >= 4:
                    result.append({
                        "code": item[0],
                        "name": item[2],
                        "type": item[3],
                    })

            FundService._fund_list_cache = result
            FundService._fund_list_cache_time = datetime.now()

            if keyword:
                kw = keyword.lower()
                result = [f for f in result if kw in f["code"].lower() or kw in f["name"].lower()]
            return result[:limit] if limit else result
        except Exception as e:
            print(f"获取基金列表错误: {e}")
            return []

    @staticmethod
    def get_fund_info(fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基本信息
        """
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            resp = requests.get(url, timeout=15)
            resp.encoding = "utf-8"
            text = resp.text

            name_match = re.search(r'var fS_name = "(.+?)";', text)
            code_match = re.search(r'var fS_code = "(.+?)";', text)
            type_match = re.search(r'var fS_type = "(.+?)";', text)

            if not name_match or not code_match:
                return None

            return {
                "code": code_match.group(1),
                "name": name_match.group(1),
                "type": type_match.group(1) if type_match else "未知",
                "updated_at": datetime.now(),
            }
        except Exception as e:
            print(f"获取基金信息错误: {e}")
            return None

    @staticmethod
    def _filter_nav_outliers(data: List[Dict]) -> None:
        """
        过滤 eastmoney 数据源中的异常净值跳变点。
        检测逻辑：某段净值与前后正常区间差异超过 50%，且没有拆分/分红标注，
        则视为数据错误，用前后正常值线性插值平滑。
        """
        if len(data) < 5:
            return

        i = 1
        while i < len(data) - 1:
            prev_nav = float(data[i - 1].get("y", 0))
            curr_nav = float(data[i].get("y", 0))
            unit_money = data[i].get("unitMoney", "")
            has_action = unit_money and any(k in unit_money for k in ["拆分", "折算", "分拆", "分红"])

            if prev_nav > 0 and abs(curr_nav - prev_nav) / prev_nav > 0.5 and not has_action:
                # 寻找异常段的结束点
                j = i + 1
                while j < len(data):
                    next_nav = float(data[j].get("y", 0))
                    next_um = data[j].get("unitMoney", "")
                    next_has_action = next_um and any(k in next_um for k in ["拆分", "折算", "分拆", "分红"])
                    # 如果回到接近前一个正常点的范围，说明异常段结束
                    if abs(next_nav - prev_nav) / prev_nav < 0.15 or next_has_action:
                        break
                    j += 1

                if j < len(data):
                    # 异常段从 i 到 j-1，用线性插值替换
                    start_nav = prev_nav
                    end_nav = float(data[j].get("y", 0))
                    days = j - i + 1
                    for k in range(i, j):
                        ratio = (k - i + 1) / days
                        interpolated = start_nav + (end_nav - start_nav) * ratio
                        data[k]["y"] = round(interpolated, 4)
                        data[k]["equityReturn"] = 0
                    i = j
                else:
                    i += 1
            else:
                i += 1

    @staticmethod
    def get_fund_history(fund_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """
        获取基金历史净值数据（含复权净值）
        复权净值 = 单位净值 × 复权因子
        复权因子累积处理：份额拆分 + 分红再投资
        """
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            resp = requests.get(url, timeout=15)
            resp.encoding = "utf-8"
            text = resp.text

            data = FundService._parse_js_var(text, "Data_netWorthTrend")
            if data is None:
                return []

            # 过滤数据源中的异常净值跳变（如 eastmoney 数据错误）
            FundService._filter_nav_outliers(data)

            result = []
            factor = 1.0
            start_ts = datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000 if start_date else 0
            end_ts = datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000 if end_date else float("inf")

            for i, item in enumerate(data):
                ts = item.get("x", 0)
                if ts < start_ts or ts > end_ts:
                    continue
                dt = datetime.fromtimestamp(ts / 1000)
                nav = float(item.get("y", 0))
                unit_money = item.get("unitMoney", "")

                # 处理份额拆分：复权因子 × 拆分比例
                # eastmoney 文本格式多样："拆分：每份基金份额折算X份" 或 "拆分：每份基金份额分拆X份"
                if unit_money and ("拆分" in unit_money or "折算" in unit_money or "分拆" in unit_money):
                    match = re.search(r"(?:折算|分拆)([0-9.]+)份", unit_money)
                    if match:
                        factor *= float(match.group(1))

                # 处理分红：假设分红再投资
                # 复权因子 × (除权前净值 / 除权参考价)
                # 其中除权前净值取前一日单位净值，除权参考价 = 除权前净值 - 每份分红
                if unit_money and "分红" in unit_money:
                    match = re.search(r"派现金([0-9.]+)元", unit_money)
                    if match:
                        dividend = float(match.group(1))
                        prev_nav = float(data[i - 1]["y"]) if i > 0 else nav
                        ex_ref = prev_nav - dividend
                        if ex_ref > 0:
                            factor *= prev_nav / ex_ref

                adjusted_nav = round(nav * factor, 4)

                result.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "nav": nav,
                    "adjusted_nav": adjusted_nav,
                    "change_percent": float(item.get("equityReturn", 0)),
                })

            return result
        except Exception as e:
            print(f"获取基金历史数据错误: {e}")
            return None

    @staticmethod
    def get_all_fund_list() -> List[Dict[str, str]]:
        """获取全部基金列表（用于定时任务缓存）"""
        return FundService.get_fund_list(limit=None)

    @staticmethod
    def _analyze_single_fund(fund: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """分析单只基金的历史低位指标"""
        code = fund["code"]
        name = fund.get("name", code)
        try:
            # 优先从数据库读取
            from services.data_service import DataService
            data = DataService.load_fund_from_database(code, "1900-01-01", "2099-12-31")

            # 数据库数据不足时从 API 补充（扫描时不写入数据库，避免并发锁竞争）
            if not data or len(data) < 100:
                api_data = FundService.get_fund_history(code, None, None)
                if api_data and len(api_data) >= 100:
                    data = api_data
                else:
                    return None

            if len(data) < 100:
                return None

            values = [item["adjusted_nav"] for item in data]
            current = values[-1]
            peak = max(values)
            trough = min(values)

            if peak <= 0 or current <= 0:
                return None

            drawdown = (peak - current) / peak * 100

            # 历史百分位：当前值在历史序列中的位置（越低越接近历史低位）
            count_lower = sum(1 for v in values if v < current)
            percentile = count_lower / len(values) * 100

            peak_date = data[values.index(peak)]["date"]
            current_date = data[-1]["date"]
            first_date = data[0]["date"]

            return {
                "code": code,
                "name": name,
                "fund_type": fund.get("type", "未知"),
                "current": round(current, 4),
                "peak": round(peak, 4),
                "trough": round(trough, 4),
                "drawdown": round(drawdown, 2),
                "percentile": round(percentile, 2),
                "peak_date": peak_date,
                "current_date": current_date,
                "first_date": first_date,
                "history_days": len(data),
            }
        except Exception as e:
            print(f"分析基金 {code} 错误: {e}")
            return None

    @staticmethod
    def scan_low_position_funds(
        limit: int = 50,
        max_scan: Optional[int] = None,
        min_history_days: int = 730,
        exclude_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        扫描全市场基金，找出处于历史低位的基金
        默认排除货币型基金（不可能出现大幅回撤）
        使用多线程并行请求以提高扫描速度
        """
        if exclude_types is None:
            exclude_types = ["货币型"]

        fund_list = FundService.get_fund_list(limit=None)
        if not fund_list:
            return []

        # 排除指定类型的基金
        filtered = [
            f for f in fund_list
            if not any(exclude in f.get("type", "") for exclude in exclude_types)
        ]

        # 取前 max_scan 只基金进行扫描，None 表示扫描全部
        sample = filtered[:max_scan] if max_scan else filtered

        results = []
        processed = 0
        total = len(sample)

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(FundService._analyze_single_fund, f): f for f in sample}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    if result and result["history_days"] >= min_history_days:
                        results.append(result)
                except Exception:
                    pass
                processed += 1
                if processed % 500 == 0:
                    print(f"低位基金扫描进度: {processed}/{total}")

        # 按回撤幅度降序排列（回撤越大越接近历史低位）
        results.sort(key=lambda x: x["drawdown"], reverse=True)
        return {"results": results[:limit], "total_scanned": total}

    @staticmethod
    def get_fund_holdings(fund_code: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取基金持仓数据（前十大重仓股）
        """
        try:
            url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.encoding = "utf-8"
            text = resp.text

            match = re.search(r'var apidata\s*=\s*(\{.+?\});', text, re.DOTALL)
            if not match:
                return None

            raw = match.group(1)
            content_match = re.search(r'content\s*:\s*"(.+?)"\s*,\s*', raw, re.DOTALL)
            if not content_match:
                return None

            html = content_match.group(1).replace('\\"', '"').replace('\\/', '/')
            tbody_match = re.search(r'<tbody>(.+?)</tbody>', html, re.DOTALL)
            if not tbody_match:
                return None

            tbody = tbody_match.group(1)
            rows = re.findall(r'<tr>(.+?)</tr>', tbody, re.DOTALL)

            holdings = []
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.+?)</td>', row, re.DOTALL)
                if len(cells) < 9:
                    continue

                # Clean each cell by removing HTML tags
                cleaned = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]

                try:
                    weight_str = cleaned[6].replace('%', '').strip()
                    weight = float(weight_str) if weight_str else 0.0
                except ValueError:
                    weight = 0.0

                holdings.append({
                    "rank": int(cleaned[0]) if cleaned[0].isdigit() else 0,
                    "stock_code": cleaned[1],
                    "stock_name": cleaned[2],
                    "weight": round(weight, 2),
                    "shares": cleaned[7],
                    "market_value": cleaned[8],
                })

            return holdings
        except Exception as e:
            print(f"获取基金持仓错误: {e}")
            return None

    @staticmethod
    def get_fund_realtime_estimate(fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金实时估值（估算净值及涨跌幅）
        数据来源: fundgz.1234567.com.cn
        """
        try:
            url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.encoding = "utf-8"
            text = resp.text

            match = re.search(r'jsonpgz\((.+?)\);', text, re.DOTALL)
            if not match:
                return None

            data = json.loads(match.group(1))
            return {
                "fund_code": data.get("fundcode"),
                "name": data.get("name"),
                "last_nav_date": data.get("jzrq"),
                "last_nav": float(data.get("dwjz", 0)) or None,
                "estimate_nav": float(data.get("gsz", 0)) or None,
                "estimate_change": float(data.get("gszzl", 0)) or None,
                "estimate_time": data.get("gztime"),
            }
        except Exception as e:
            print(f"获取基金实时估值错误: {e}")
            return None
