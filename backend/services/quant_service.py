import akshare as ak
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from services.cache_service import CacheService
import json

# 预置主流 A 股列表（用于综合评分推荐，约170只去重）
_POPULAR_STOCKS = [
    {"code": "600519", "name": "贵州茅台"}, {"code": "000858", "name": "五粮液"},
    {"code": "601318", "name": "中国平安"}, {"code": "000333", "name": "美的集团"},
    {"code": "601888", "name": "中国中免"}, {"code": "600036", "name": "招商银行"},
    {"code": "000001", "name": "平安银行"}, {"code": "600276", "name": "恒瑞医药"},
    {"code": "002594", "name": "比亚迪"}, {"code": "300750", "name": "宁德时代"},
    {"code": "600030", "name": "中信证券"}, {"code": "601012", "name": "隆基绿能"},
    {"code": "600887", "name": "伊利股份"}, {"code": "002415", "name": "海康威视"},
    {"code": "000568", "name": "泸州老窖"}, {"code": "601166", "name": "兴业银行"},
    {"code": "600900", "name": "长江电力"}, {"code": "601398", "name": "工商银行"},
    {"code": "000002", "name": "万科A"}, {"code": "002714", "name": "牧原股份"},
    {"code": "300059", "name": "东方财富"}, {"code": "601899", "name": "紫金矿业"},
    {"code": "600309", "name": "万华化学"}, {"code": "002352", "name": "顺丰控股"},
    {"code": "601288", "name": "农业银行"}, {"code": "600048", "name": "保利发展"},
    {"code": "002142", "name": "宁波银行"}, {"code": "601668", "name": "中国建筑"},
    {"code": "002230", "name": "科大讯飞"}, {"code": "600809", "name": "山西汾酒"},
    {"code": "300760", "name": "迈瑞医疗"}, {"code": "601816", "name": "京沪高铁"},
    {"code": "002812", "name": "恩捷股份"}, {"code": "600031", "name": "三一重工"},
    {"code": "002460", "name": "赣锋锂业"}, {"code": "601939", "name": "建设银行"},
    {"code": "601088", "name": "中国神华"}, {"code": "002271", "name": "东方雨虹"},
    {"code": "603259", "name": "药明康德"}, {"code": "600436", "name": "片仔癀"},
    {"code": "300274", "name": "阳光电源"}, {"code": "600585", "name": "海螺水泥"},
    {"code": "002304", "name": "洋河股份"}, {"code": "600570", "name": "恒生电子"},
    {"code": "601728", "name": "中国电信"}, {"code": "601857", "name": "中国石油"},
    {"code": "600028", "name": "中国石化"}, {"code": "601633", "name": "长城汽车"},
    {"code": "002049", "name": "紫光国微"}, {"code": "603288", "name": "海天味业"},
    {"code": "601818", "name": "光大银行"}, {"code": "601211", "name": "国泰君安"},
    {"code": "601336", "name": "新华保险"}, {"code": "600016", "name": "民生银行"},
    {"code": "601988", "name": "中国银行"}, {"code": "601328", "name": "交通银行"},
    {"code": "601601", "name": "中国太保"}, {"code": "601628", "name": "中国人寿"},
    {"code": "600000", "name": "浦发银行"}, {"code": "601229", "name": "上海银行"},
    {"code": "600999", "name": "招商证券"}, {"code": "601066", "name": "中信建投"},
    {"code": "601995", "name": "中金公司"}, {"code": "600438", "name": "通威股份"},
    {"code": "300014", "name": "亿纬锂能"}, {"code": "002709", "name": "天赐材料"},
    {"code": "300073", "name": "当升科技"}, {"code": "002074", "name": "国轩高科"},
    {"code": "002050", "name": "三花智控"}, {"code": "603806", "name": "福斯特"},
    {"code": "300033", "name": "同花顺"}, {"code": "688111", "name": "金山办公"},
    {"code": "600588", "name": "用友网络"}, {"code": "000938", "name": "紫光股份"},
    {"code": "000977", "name": "浪潮信息"}, {"code": "603019", "name": "中科曙光"},
    {"code": "300496", "name": "中科创达"}, {"code": "300308", "name": "中际旭创"},
    {"code": "002236", "name": "大华股份"}, {"code": "300454", "name": "深信服"},
    {"code": "688777", "name": "中控技术"}, {"code": "300124", "name": "汇川技术"},
    {"code": "601669", "name": "中国电建"}, {"code": "601390", "name": "中国中铁"},
    {"code": "601800", "name": "中国交建"}, {"code": "601186", "name": "中国铁建"},
    {"code": "601618", "name": "中国中冶"}, {"code": "601117", "name": "中国化学"},
    {"code": "601868", "name": "中国能建"}, {"code": "601989", "name": "中国重工"},
    {"code": "600150", "name": "中国船舶"}, {"code": "600893", "name": "航发动力"},
    {"code": "600760", "name": "中航沈飞"}, {"code": "000768", "name": "中航西飞"},
    {"code": "002179", "name": "中航光电"}, {"code": "600862", "name": "中航高科"},
    {"code": "600702", "name": "舍得酒业"}, {"code": "000596", "name": "古井贡酒"},
    {"code": "600779", "name": "水井坊"}, {"code": "603369", "name": "今世缘"},
    {"code": "600600", "name": "青岛啤酒"}, {"code": "002568", "name": "百润股份"},
    {"code": "002507", "name": "涪陵榨菜"}, {"code": "300999", "name": "金龙鱼"},
    {"code": "603517", "name": "绝味食品"}, {"code": "002557", "name": "洽洽食品"},
    {"code": "600132", "name": "重庆啤酒"}, {"code": "603345", "name": "安井食品"},
    {"code": "002847", "name": "盐津铺子"}, {"code": "605499", "name": "东鹏饮料"},
    {"code": "600298", "name": "安琪酵母"}, {"code": "300146", "name": "汤臣倍健"},
    {"code": "300122", "name": "智飞生物"}, {"code": "600196", "name": "复星医药"},
    {"code": "000661", "name": "长春高新"}, {"code": "300347", "name": "泰格医药"},
    {"code": "300896", "name": "爱美客"}, {"code": "000538", "name": "云南白药"},
    {"code": "600085", "name": "同仁堂"}, {"code": "000963", "name": "华东医药"},
    {"code": "300003", "name": "乐普医疗"}, {"code": "002007", "name": "华兰生物"},
    {"code": "603392", "name": "万泰生物"}, {"code": "600276", "name": "恒瑞医药"},
    {"code": "601169", "name": "北京银行"}, {"code": "601009", "name": "南京银行"},
    {"code": "600919", "name": "江苏银行"}, {"code": "601838", "name": "成都银行"},
    {"code": "600926", "name": "杭州银行"}, {"code": "601998", "name": "中信银行"},
    {"code": "601658", "name": "邮储银行"}, {"code": "600015", "name": "华夏银行"},
    {"code": "601916", "name": "浙商银行"}, {"code": "601577", "name": "长沙银行"},
    {"code": "002948", "name": "青岛银行"}, {"code": "600928", "name": "西安银行"},
    {"code": "300763", "name": "锦浪科技"}, {"code": "300316", "name": "晶盛机电"},
    {"code": "002459", "name": "晶澳科技"}, {"code": "002129", "name": "TCL中环"},
    {"code": "000591", "name": "太阳能"}, {"code": "601865", "name": "福莱特"},
    {"code": "688599", "name": "天合光能"}, {"code": "688223", "name": "晶科能源"},
    {"code": "300118", "name": "东方日升"}, {"code": "600498", "name": "烽火通信"},
    {"code": "002405", "name": "四维图新"}, {"code": "300339", "name": "润和软件"},
    {"code": "688561", "name": "奇安信"}, {"code": "300676", "name": "华大基因"},
    {"code": "600438", "name": "通威股份"}, {"code": "600482", "name": "中国动力"},
    {"code": "300724", "name": "捷佳伟创"}, {"code": "603659", "name": "璞泰来"},
    {"code": "002240", "name": "盛新锂能"}, {"code": "002056", "name": "横店东磁"},
]

# 去重
_seen = set()
_POPULAR_STOCKS = [s for s in _POPULAR_STOCKS if s["code"] not in _seen and not _seen.add(s["code"])]

# 智能选股类型映射到 akshare 接口
_SCREEN_TYPE_MAP = {
    "cxg": {"func": "stock_rank_cxg_ths", "label": "创新高"},
    "cxd": {"func": "stock_rank_cxd_ths", "label": "创新低"},
    "cxfl": {"func": "stock_rank_cxfl_ths", "label": "持续放量"},
    "cxsl": {"func": "stock_rank_cxsl_ths", "label": "持续缩量"},
    "ljqs": {"func": "stock_rank_ljqs_ths", "label": "量价齐升"},
    "ljqd": {"func": "stock_rank_ljqd_ths", "label": "量价齐跌"},
    "lxsz": {"func": "stock_rank_lxsz_ths", "label": "连续上涨"},
    "lxxd": {"func": "stock_rank_lxxd_ths", "label": "连续下跌"},
    "xstp": {"func": "stock_rank_xstp_ths", "label": "向上突破"},
    "xxtp": {"func": "stock_rank_xxtp_ths", "label": "向下突破"},
    "xzjp": {"func": "stock_rank_xzjp_ths", "label": "险资举牌"},
}


class QuantService:
    """量化分析服务类"""

    # ========== 模块1：智能选股 ==========

    @staticmethod
    def get_smart_screen(screen_type: str) -> List[Dict[str, Any]]:
        """
        智能选股 - 调用 akshare 的 stock_rank_* 接口
        screen_type: cxg/cxd/cxfl/cxsl/ljqs/ljqd/lxsz/lxxd/xstp/xxtp/xzjp
        """
        try:
            config = _SCREEN_TYPE_MAP.get(screen_type)
            if not config:
                return []

            # 检查缓存
            cached = CacheService.get_cached_quant(f"screen:{screen_type}")
            if cached:
                return cached

            func_name = config["func"]
            func = getattr(ak, func_name, None)
            if func is None:
                print(f"akshare 不存在接口: {func_name}")
                return []

            df = func()
            if df is None or df.empty:
                return []

            # akshare stock_rank_* 返回的 DataFrame 第一行可能是重复表头，过滤掉
            # 列名通常是: 序号, 股票代码, 股票简称, 涨跌幅, 最新价, ...
            # 先过滤掉序号列值等于 "序号" 的重复表头行
            if "序号" in df.columns:
                df = df[df["序号"] != "序号"]

            def safe_float(val):
                try:
                    v = float(val)
                    return 0 if v != v else v  # NaN check
                except (ValueError, TypeError):
                    return 0

            result = []
            for _, row in df.head(50).iterrows():
                item = {
                    "code": "",
                    "name": "",
                    "price": 0,
                    "change_percent": 0,
                    "turnover_rate": 0,
                    "screen_type": screen_type,
                    "screen_label": config["label"],
                }

                # 按列名提取
                if "股票代码" in df.columns:
                    item["code"] = str(row["股票代码"]).strip()
                if "股票简称" in df.columns:
                    item["name"] = str(row["股票简称"]).strip()
                if "最新价" in df.columns:
                    item["price"] = safe_float(row["最新价"])
                if "涨跌幅" in df.columns:
                    item["change_percent"] = safe_float(row["涨跌幅"])
                if "换手率" in df.columns:
                    item["turnover_rate"] = safe_float(row["换手率"])

                if item["code"]:
                    result.append(item)

            # 缓存5分钟
            CacheService.set_cached_quant(f"screen:{screen_type}", result, ttl=300)
            return result
        except Exception as e:
            print(f"智能选股错误 ({screen_type}): {e}")
            return []

    @staticmethod
    def get_hot_stocks() -> List[Dict[str, Any]]:
        """东方财富人气榜"""
        try:
            cached = CacheService.get_cached_quant("hot_stocks")
            if cached:
                return cached

            df = ak.stock_hot_rank_em()
            if df is None or df.empty:
                return []

            def safe_float(val):
                try:
                    v = float(val)
                    return 0 if v != v else v  # NaN check
                except (ValueError, TypeError):
                    return 0

            def safe_int(val):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return 0

            result = []
            for idx, row in df.head(50).iterrows():
                item = {
                    "rank": idx + 1,
                    "code": "",
                    "name": "",
                    "price": 0,
                    "change_percent": 0,
                    "hot_rank": 0,
                }

                # 按列名提取
                if "股票代码" in df.columns:
                    item["code"] = str(row["股票代码"]).strip()
                if "股票简称" in df.columns:
                    item["name"] = str(row["股票简称"]).strip()
                if "最新价" in df.columns:
                    item["price"] = safe_float(row["最新价"])
                if "涨跌幅" in df.columns:
                    item["change_percent"] = safe_float(row["涨跌幅"])
                if "人气排名" in df.columns:
                    item["hot_rank"] = safe_int(row["人气排名"])

                if item["code"]:
                    result.append(item)

            CacheService.set_cached_quant("hot_stocks", result, ttl=300)
            return result
        except Exception as e:
            print(f"获取人气榜错误: {e}")
            return []

    @staticmethod
    def get_market_valuation() -> Dict[str, Any]:
        """全市场估值统计"""
        try:
            cached = CacheService.get_cached_quant("market_valuation")
            if cached:
                return cached

            result = {
                "pe_ttm_median": 0,
                "pb_median": 0,
                "dividend_yield": 0,
                "broken_net_count": 0,
                "total_count": 0,
                "pe_percentile": 0,
                "pb_percentile": 0,
            }

            # 全市场 PE (列名: middlePETTM, quantileInRecent10YearsMiddlePeTtm 等)
            try:
                df_pe = ak.stock_a_ttm_lyr()
                if df_pe is not None and not df_pe.empty:
                    last = df_pe.iloc[-1]
                    if "middlePETTM" in df_pe.columns:
                        result["pe_ttm_median"] = round(float(last["middlePETTM"]), 2)
                    if "quantileInRecent10YearsMiddlePeTtm" in df_pe.columns:
                        result["pe_percentile"] = round(float(last["quantileInRecent10YearsMiddlePeTtm"]) * 100, 1)
            except Exception as e:
                print(f"获取PE数据错误: {e}")

            # 全市场 PB (列名: middlePB, quantileInRecent10YearsMiddlePB 等)
            try:
                df_pb = ak.stock_a_all_pb()
                if df_pb is not None and not df_pb.empty:
                    last = df_pb.iloc[-1]
                    if "middlePB" in df_pb.columns:
                        result["pb_median"] = round(float(last["middlePB"]), 2)
                    if "quantileInRecent10YearsMiddlePB" in df_pb.columns:
                        result["pb_percentile"] = round(float(last["quantileInRecent10YearsMiddlePB"]) * 100, 1)
            except Exception as e:
                print(f"获取PB数据错误: {e}")

            # 全市场股息率 (列名: 日期, 股息率)
            try:
                df_div = ak.stock_a_gxl_lg()
                if df_div is not None and not df_div.empty:
                    if "股息率" in df_div.columns:
                        result["dividend_yield"] = round(float(df_div["股息率"].iloc[-1]), 2)
            except Exception as e:
                print(f"获取股息率数据错误: {e}")

            CacheService.set_cached_quant("market_valuation", result, ttl=3600)
            return result
        except Exception as e:
            print(f"获取市场估值错误: {e}")
            return {}

    # ========== 模块2：多因子选股 ==========

    @staticmethod
    def _ensure_bs_login():
        """确保 baostock 已登录"""
        try:
            lg = bs.login()
            return lg.error_code == "0"
        except:
            return False

    @staticmethod
    def _to_baostock_code(code: str) -> str:
        """纯代码转为 baostock 格式"""
        prefix = "sh" if code.startswith("6") else "sz"
        return f"{prefix}.{code}"

    @staticmethod
    def _fetch_stock_fundamental(code: str) -> Optional[Dict[str, Any]]:
        """获取单只股票的基本面数据（baostock）"""
        try:
            QuantService._ensure_bs_login()
            bs_code = QuantService._to_baostock_code(code)

            # 获取最近的盈利数据
            recent_year = datetime.now().year
            recent_quarter = (datetime.now().month - 1) // 3
            if recent_quarter == 0:
                recent_year -= 1
                recent_quarter = 4

            pe_ttm = 0
            pb = 0
            roe = 0
            net_profit_margin = 0
            revenue_growth = 0
            net_profit_growth = 0
            debt_ratio = 0
            dividend_yield = 0

            # 盈利数据
            try:
                rs = bs.query_profit_data(code=bs_code, year=recent_year, quarter=recent_quarter)
                while rs.error_code == "0" and rs.next():
                    row = rs.get_row_data()
                    if len(row) > 6:
                        try:
                            roe = float(row[6]) if row[6] else 0
                        except:
                            pass
                    if len(row) > 5:
                        try:
                            net_profit_margin = float(row[5]) if row[5] else 0
                        except:
                            pass
            except:
                pass

            # 成长数据
            try:
                rs = bs.query_growth_data(code=bs_code, year=recent_year, quarter=recent_quarter)
                while rs.error_code == "0" and rs.next():
                    row = rs.get_row_data()
                    if len(row) > 3:
                        try:
                            revenue_growth = float(row[3]) if row[3] else 0
                        except:
                            pass
                    if len(row) > 5:
                        try:
                            net_profit_growth = float(row[5]) if row[5] else 0
                        except:
                            pass
            except:
                pass

            # 偿债数据
            try:
                rs = bs.query_balance_data(code=bs_code, year=recent_year, quarter=recent_quarter)
                while rs.error_code == "0" and rs.next():
                    row = rs.get_row_data()
                    if len(row) > 2:
                        try:
                            debt_ratio = float(row[2]) if row[2] else 0
                        except:
                            pass
            except:
                pass

            # K线数据获取估值（最近一天）
            try:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,peTTM,pbMRQ,psTTM",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                )
                last_row = None
                while rs.error_code == "0" and rs.next():
                    last_row = rs.get_row_data()
                if last_row:
                    if len(last_row) > 1 and last_row[1]:
                        try:
                            pe_ttm = float(last_row[1])
                        except:
                            pass
                    if len(last_row) > 2 and last_row[2]:
                        try:
                            pb = float(last_row[2])
                        except:
                            pass
            except:
                pass

            # 股息率 - 尝试从百度估值接口获取
            try:
                bs_code_simple = code  # 纯代码
                df_val = ak.stock_zh_valuation_baidu(symbol=bs_code_simple, indicator="总市值")
                # 这个接口可能不直接返回股息率，跳过
            except:
                pass

            return {
                "code": code,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "pe_ttm": round(pe_ttm, 2) if pe_ttm else 0,
                "pb": round(pb, 2) if pb else 0,
                "roe": round(roe, 4) if roe else 0,
                "net_profit_margin": round(net_profit_margin, 4) if net_profit_margin else 0,
                "revenue_growth": round(revenue_growth, 4) if revenue_growth else 0,
                "net_profit_growth": round(net_profit_growth, 4) if net_profit_growth else 0,
                "debt_ratio": round(debt_ratio, 4) if debt_ratio else 0,
                "dividend_yield": round(dividend_yield, 2) if dividend_yield else 0,
            }
        except Exception as e:
            print(f"获取基本面数据错误 ({code}): {e}")
            return None

    @staticmethod
    def _calculate_score(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算综合评分
        5维度评分: 估值25% + 盈利25% + 成长25% + 偿债15% + 股息10%
        """
        # 估值评分 (PE/PB 越低越好)
        valuation_score = 0
        if data.get("pe_ttm") and data["pe_ttm"] > 0:
            if data["pe_ttm"] < 10:
                valuation_score = 90
            elif data["pe_ttm"] < 20:
                valuation_score = 70
            elif data["pe_ttm"] < 30:
                valuation_score = 50
            elif data["pe_ttm"] < 50:
                valuation_score = 30
            else:
                valuation_score = 10
        if data.get("pb") and data["pb"] > 0:
            if data["pb"] < 1:
                valuation_score = min(95, valuation_score + 20)
            elif data["pb"] < 2:
                valuation_score = min(95, valuation_score + 10)

        # 盈利评分 (ROE/净利率)
        profit_score = 0
        roe_val = data.get("roe", 0) or 0
        npm_val = data.get("net_profit_margin", 0) or 0
        if roe_val > 0.15:
            profit_score = 90
        elif roe_val > 0.10:
            profit_score = 70
        elif roe_val > 0.05:
            profit_score = 50
        elif roe_val > 0:
            profit_score = 30
        if npm_val > 0.15:
            profit_score = min(100, profit_score + 10)
        elif npm_val > 0.05:
            profit_score = min(100, profit_score + 5)

        # 成长评分 (营收增速/利润增速)
        growth_score = 0
        rev_g = data.get("revenue_growth", 0) or 0
        np_g = data.get("net_profit_growth", 0) or 0
        avg_growth = (rev_g + np_g) / 2
        if avg_growth > 0.30:
            growth_score = 90
        elif avg_growth > 0.15:
            growth_score = 70
        elif avg_growth > 0.05:
            growth_score = 50
        elif avg_growth > 0:
            growth_score = 30
        else:
            growth_score = 10

        # 偿债评分 (资产负债率越低越好)
        debt_score = 0
        debt_val = data.get("debt_ratio", 0) or 0
        if debt_val < 0.30:
            debt_score = 90
        elif debt_val < 0.50:
            debt_score = 70
        elif debt_val < 0.70:
            debt_score = 50
        else:
            debt_score = 30

        # 股息评分
        dividend_score = 0
        div_val = data.get("dividend_yield", 0) or 0
        if div_val > 5:
            dividend_score = 90
        elif div_val > 3:
            dividend_score = 70
        elif div_val > 1:
            dividend_score = 50
        elif div_val > 0:
            dividend_score = 30

        # 加权总分
        total_score = (
            valuation_score * 0.25
            + profit_score * 0.25
            + growth_score * 0.25
            + debt_score * 0.15
            + dividend_score * 0.10
        )

        return {
            **data,
            "valuation_score": round(valuation_score, 1),
            "profit_score": round(profit_score, 1),
            "growth_score": round(growth_score, 1),
            "debt_score": round(debt_score, 1),
            "dividend_score": round(dividend_score, 1),
            "total_score": round(total_score, 1),
        }

    @staticmethod
    def get_stock_fundamental_screen(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        多因子筛选
        filters: pe_min, pe_max, pb_min, pb_max, roe_min, revenue_growth_min,
                 net_profit_growth_min, dividend_yield_min, debt_ratio_max
        """
        try:
            # 检查缓存
            cache_key = f"fundamental_screen:{json.dumps(filters, sort_keys=True)}"
            cached = CacheService.get_cached_quant(cache_key)
            if cached:
                return cached

            QuantService._ensure_bs_login()
            results = []

            # 获取全市场股票列表
            rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
            all_codes = []
            while rs.error_code == "0" and rs.next():
                row = rs.get_row_data()
                code = row[0].replace("sh.", "").replace("sz.", "")
                # 过滤ST和北交所
                name = row[1] if len(row) > 1 else ""
                if code.startswith(("6", "0", "3")) and "ST" not in name:
                    all_codes.append({"code": code, "name": name})

            # 限制扫描数量（全市场太多，取前500只沪深主板+创业板）
            scan_list = all_codes[:500]

            for stock in scan_list:
                data = QuantService._fetch_stock_fundamental(stock["code"])
                if not data:
                    continue

                # 应用筛选条件
                if filters.get("pe_min") is not None and data["pe_ttm"] < filters["pe_min"]:
                    continue
                if filters.get("pe_max") is not None and data["pe_ttm"] > filters["pe_max"]:
                    continue
                if filters.get("pb_min") is not None and data["pb"] < filters["pb_min"]:
                    continue
                if filters.get("pb_max") is not None and data["pb"] > filters["pb_max"]:
                    continue
                if filters.get("roe_min") is not None and data["roe"] < filters["roe_min"]:
                    continue
                if filters.get("revenue_growth_min") is not None and data["revenue_growth"] < filters["revenue_growth_min"]:
                    continue
                if filters.get("net_profit_growth_min") is not None and data["net_profit_growth"] < filters["net_profit_growth_min"]:
                    continue
                if filters.get("dividend_yield_min") is not None and data["dividend_yield"] < filters["dividend_yield_min"]:
                    continue
                if filters.get("debt_ratio_max") is not None and data["debt_ratio"] > filters["debt_ratio_max"]:
                    continue

                # 计算评分
                scored = QuantService._calculate_score(data)
                scored["name"] = stock["name"]
                results.append(scored)

            # 按综合评分排序
            results.sort(key=lambda x: x["total_score"], reverse=True)

            # 缓存1小时
            CacheService.set_cached_quant(cache_key, results[:50], ttl=3600)
            return results[:50]
        except Exception as e:
            print(f"多因子筛选错误: {e}")
            return []

    @staticmethod
    def get_stock_score(code: str) -> Optional[Dict[str, Any]]:
        """获取单只股票综合评分"""
        try:
            # 检查缓存
            cached = CacheService.get_cached_quant(f"score:{code}")
            if cached:
                return cached

            data = QuantService._fetch_stock_fundamental(code)
            if not data:
                return None

            # 补充名称
            name = ""
            for s in _POPULAR_STOCKS:
                if s["code"] == code:
                    name = s["name"]
                    break
            data["name"] = name

            scored = QuantService._calculate_score(data)
            CacheService.set_cached_quant(f"score:{code}", scored, ttl=3600)
            return scored
        except Exception as e:
            print(f"获取股票评分错误 ({code}): {e}")
            return None

    @staticmethod
    def get_stock_recommendation(limit: int = 20) -> List[Dict[str, Any]]:
        """综合评分排行 - 对预置列表评分排序"""
        try:
            cached = CacheService.get_cached_quant(f"recommend:{limit}")
            if cached:
                return cached

            results = []
            for stock in _POPULAR_STOCKS:
                data = QuantService._fetch_stock_fundamental(stock["code"])
                if not data:
                    continue
                scored = QuantService._calculate_score(data)
                scored["name"] = stock["name"]
                results.append(scored)

            results.sort(key=lambda x: x["total_score"], reverse=True)
            result = results[:limit]

            CacheService.set_cached_quant(f"recommend:{limit}", result, ttl=3600)
            return result
        except Exception as e:
            print(f"获取推荐排行错误: {e}")
            return []

    # ========== 模块3：基金智能推荐 ==========

    @staticmethod
    def get_fund_recommend(fund_type: str = "全部", limit: int = 20) -> List[Dict[str, Any]]:
        """基金推荐 - 结合涨幅排行 + 多指标综合排序"""
        try:
            cache_key = f"fund_recommend:{fund_type}:{limit}"
            cached = CacheService.get_cached_quant(cache_key)
            if cached:
                return cached

            # 复用 sector_service 的基金排行方法
            from services.sector_service import SectorService
            raw_funds = SectorService.get_funds_by_type(fund_type=fund_type, sort_by="daily", limit=200)
            if not raw_funds:
                return []

            result = []
            for item in raw_funds:
                # 综合评分: 近1月*30% + 近1年*30% + 成立来*0.01*20% + 日涨幅*20%
                m1 = item.get("month_change") or 0
                y1 = item.get("year_change") or 0
                total = item.get("total_change") or 0
                d1 = item.get("daily_change") or 0

                fund_score = (m1 * 0.3 + y1 * 0.3 + total * 0.01 * 0.2 + d1 * 0.2)
                item["fund_score"] = round(fund_score, 2)
                result.append(item)

            # 按综合得分排序
            result.sort(key=lambda x: x["fund_score"], reverse=True)

            result = result[:limit]
            CacheService.set_cached_quant(cache_key, result, ttl=300)
            return result
        except Exception as e:
            print(f"获取基金推荐错误: {e}")
            return []
