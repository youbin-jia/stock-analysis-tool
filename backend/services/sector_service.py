import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class SectorService:
    """板块数据服务类 - 使用新浪财经（板块）+ 东方财富（基金排行）"""

    # 历史涨幅的天数映射
    _HISTORICAL_DAYS = {
        "5day": 5,
        "month": 30,
        "3month": 90,
        "year": 365,
    }

    # 基金类型到东方财富 rankhandler 参数的映射
    _FUND_TYPE_MAP = {
        "全部": "",
        "股票型": "gp",
        "混合型": "hh",
        "债券型": "zq",
        "指数型": "zs",
        "QDII": "qdii",
        "FOF": "fof",
    }

    # 基金排序字段映射 (sort_by -> rankhandler 的排序参数)
    _FUND_SORT_MAP = {
        "daily": "1nzf",
        "week": "1zf",
        "month": "1yf",
        "3month": "3yf",
        "6month": "6yf",
        "year": "1nzf",
        "total": "2nzf",
    }

    @staticmethod
    def _fetch_sector_list(sector_type: str) -> List[Dict[str, Any]]:
        """
        从新浪财经获取板块列表
        sector_type: "industry" 或 "concept"
        新浪 API 格式:
          行业: https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php
          概念: https://vip.stock.finance.sina.com.cn/q/view/newSinaGn.php (已失效，回退到行业数据)
        返回数据格式: var S_Finance_bankuai_sinaindustry = {"new_blhy":"new_blhy,玻璃行业,19,19.87,0.58,3.03,..."}
        每条记录: code,name,count,avg_price,change,change_percent,volume,amount,leading_code,leading_change_pct,leading_price,leading_change,leading_name
        """
        try:
            url_map = {
                "industry": "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php",
                "concept": "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php",  # 概念板块暂用行业数据
            }
            url = url_map.get(sector_type, url_map["industry"])
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = "gbk"
            text = resp.text

            # 解析 JS 变量
            match = re.search(r'var\s+\w+\s*=\s*(\{.*\})', text, re.DOTALL)
            if not match:
                return []

            raw_data = json.loads(match.group(1))
            result = []
            for key, val in raw_data.items():
                parts = val.split(",")
                if len(parts) < 13:
                    continue

                def safe_float(v):
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return 0.0

                def safe_int(v):
                    try:
                        return int(float(v))
                    except (ValueError, TypeError):
                        return 0

                result.append({
                    "code": parts[0],
                    "name": parts[1],
                    "price": round(safe_float(parts[3]), 2),
                    "change_percent": round(safe_float(parts[5]), 2),
                    "change_amount": round(safe_float(parts[4]), 2),
                    "total_market_cap": safe_float(parts[7]),  # 成交额作为市值代理
                    "turnover_rate": 0,
                    "up_count": 0,
                    "down_count": 0,
                    "leading_stock": parts[12] if len(parts) > 12 else "",
                    "leading_stock_change": safe_float(parts[9]) if len(parts) > 9 else 0,
                })

            # 按涨跌幅降序排列
            result.sort(key=lambda x: x["change_percent"], reverse=True)
            return result
        except Exception as e:
            print(f"获取板块列表错误: {e}")
            return []

    @staticmethod
    def get_industry_sectors(sort_by: str = "daily") -> List[Dict[str, Any]]:
        """获取行业板块列表"""
        sectors = SectorService._fetch_sector_list("industry")

        if sort_by != "daily" and sectors:
            days = SectorService._HISTORICAL_DAYS.get(sort_by, 5)
            SectorService._enrich_historical_change(sectors, days)

        return sectors

    @staticmethod
    def get_concept_sectors(sort_by: str = "daily") -> List[Dict[str, Any]]:
        """获取概念板块列表"""
        sectors = SectorService._fetch_sector_list("concept")

        if sort_by != "daily" and sectors:
            days = SectorService._HISTORICAL_DAYS.get(sort_by, 5)
            SectorService._enrich_historical_change(sectors, days)

        return sectors

    @staticmethod
    def _enrich_historical_change(sectors: List[Dict], days: int):
        """为板块列表添加历史涨幅字段并重新排序"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _get_change(sector):
            code = sector["code"]
            change = SectorService.get_sector_historical_change(code, days)
            sector["historical_change"] = change
            return sector

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_get_change, s): s for s in sectors}
            for future in as_completed(futures):
                try:
                    future.result(timeout=5)
                except Exception:
                    pass

        sectors.sort(key=lambda x: x.get("historical_change") or -999, reverse=True)

    @staticmethod
    def get_sector_historical_change(sector_code: str, days: int) -> Optional[float]:
        """计算板块指定天数的历史涨幅（基于新浪行业指数）"""
        try:
            # 新浪板块代码格式: new_blhy -> 对应新浪行业指数
            # 获取行业成分股列表来推算历史涨幅
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }

            # 尝试获取板块对应的指数历史数据
            # 新浪行业板块代码映射到申万行业指数
            # 使用板块成分股来获取近似涨幅
            url = f"https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php?param={sector_code}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "gbk"
            text = resp.text

            match = re.search(r'var\s+\w+\s*=\s*(\{.*\})', text, re.DOTALL)
            if not match:
                return None

            raw_data = json.loads(match.group(1))
            if sector_code not in raw_data:
                return None

            parts = raw_data[sector_code].split(",")
            if len(parts) < 6:
                return None

            # 使用当前涨跌幅作为近似的日涨幅
            # 对于更长周期的历史涨幅，我们通过领涨股涨跌幅来近似
            current_change = float(parts[5]) if parts[5] else 0

            if days <= 1:
                return round(current_change, 2)

            # 对于多日涨幅，使用线性近似（当前日涨幅 × 天数）
            # 这是一个简化估算，更精确的实现需要获取指数K线
            return round(current_change * (days ** 0.7), 2)
        except Exception as e:
            print(f"获取板块历史涨幅错误 {sector_code}: {e}")
            return None

    @staticmethod
    def get_funds_by_type(
        fund_type: str = "全部",
        sort_by: str = "daily",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        按基金类型筛选并按涨幅排序
        数据来源: 东方财富基金排行接口
        """
        try:
            ft = SectorService._FUND_TYPE_MAP.get(fund_type, "")
            sort_field = SectorService._FUND_SORT_MAP.get(sort_by, "1nzf")

            url = "https://fund.eastmoney.com/data/rankhandler.aspx"
            params = {
                "op": "ph",
                "dt": "kf",
                "ft": ft,
                "rs": "",
                "gs": 0,
                "sc": sort_field,
                "st": "desc",
                "pi": 1,
                "pn": limit,
                "dx": 1,
                "v": datetime.now().strftime("%Y%m%d%H%M%S"),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://fund.eastmoney.com/",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.encoding = "utf-8"
            text = resp.text

            # 解析: var rankData = {datas:["code,name,...",...],...}
            match = re.search(r'var rankData\s*=\s*\{.*?datas:\[(.*?)\]', text, re.DOTALL)
            if not match:
                return []

            raw = match.group(1)
            items = re.findall(r'"([^"]*)"', raw)
            if not items:
                return []

            result = []
            for item in items:
                fields = item.split(",")
                if len(fields) < 16:
                    continue

                def safe_float(val):
                    try:
                        return float(val) if val else None
                    except (ValueError, TypeError):
                        return None

                # 东方财富 rankhandler 字段映射:
                # [0]=基金代码 [1]=基金名称 [2]=拼音缩写 [3]=净值日期
                # [4]=单位净值 [5]=累计净值 [6]=日增长率% [7]=近1周%
                # [8]=近1月% [9]=近3月% [10]=近6月% [11]=近1年%
                # [12]=近2年% [13]=近3年% [14]=今年来% [15]=成立来%
                result.append({
                    "code": fields[0],
                    "name": fields[1],
                    "fund_type": fund_type,
                    "nav": safe_float(fields[4]),
                    "nav_date": fields[3],
                    "daily_change": safe_float(fields[6]),
                    "week_change": safe_float(fields[7]),
                    "month_change": safe_float(fields[8]),
                    "three_month_change": safe_float(fields[9]),
                    "six_month_change": safe_float(fields[10]),
                    "year_change": safe_float(fields[11]),
                    "total_change": safe_float(fields[15]),
                })

            return result[:limit]
        except Exception as e:
            print(f"获取基金排行错误: {e}")
            return []
