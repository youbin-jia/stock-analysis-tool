import requests
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 预置主流 A 股列表（当外部数据源不可用时作为 fallback）
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
    {"code": "601995", "name": "中金公司"}, {"code": "601162", "name": "天风证券"},
    {"code": "600837", "name": "海通证券"}, {"code": "601377", "name": "兴业证券"},
    {"code": "601881", "name": "中国银河"}, {"code": "600109", "name": "国金证券"},
    {"code": "601236", "name": "红塔证券"}, {"code": "601901", "name": "方正证券"},
    {"code": "601788", "name": "光大证券"}, {"code": "601198", "name": "东兴证券"},
    {"code": "002673", "name": "西部证券"}, {"code": "000776", "name": "广发证券"},
    {"code": "002926", "name": "华西证券"}, {"code": "002500", "name": "山西证券"},
    {"code": "002797", "name": "第一创业"}, {"code": "000728", "name": "国元证券"},
    {"code": "000783", "name": "长江证券"}, {"code": "002939", "name": "长城证券"},
    {"code": "000987", "name": "越秀资本"}, {"code": "002670", "name": "国盛金控"},
    {"code": "000750", "name": "国海证券"}, {"code": "601169", "name": "北京银行"},
    {"code": "601009", "name": "南京银行"}, {"code": "600919", "name": "江苏银行"},
    {"code": "601838", "name": "成都银行"}, {"code": "601077", "name": "渝农商行"},
    {"code": "600926", "name": "杭州银行"}, {"code": "002807", "name": "江阴银行"},
    {"code": "002839", "name": "张家港行"}, {"code": "603323", "name": "苏农银行"},
    {"code": "601128", "name": "常熟银行"}, {"code": "002958", "name": "青农商行"},
    {"code": "601825", "name": "沪农商行"}, {"code": "601665", "name": "齐鲁银行"},
    {"code": "600908", "name": "无锡银行"}, {"code": "601963", "name": "重庆银行"},
    {"code": "601187", "name": "厦门银行"}, {"code": "600928", "name": "西安银行"},
    {"code": "002948", "name": "青岛银行"}, {"code": "601998", "name": "中信银行"},
    {"code": "601658", "name": "邮储银行"}, {"code": "600015", "name": "华夏银行"},
    {"code": "601916", "name": "浙商银行"}, {"code": "601577", "name": "长沙银行"},
    {"code": "601860", "name": "紫金银行"}, {"code": "002936", "name": "郑州银行"},
    {"code": "002966", "name": "苏州银行"}, {"code": "601528", "name": "瑞丰银行"},
    {"code": "600438", "name": "通威股份"}, {"code": "300014", "name": "亿纬锂能"},
    {"code": "002709", "name": "天赐材料"}, {"code": "603659", "name": "璞泰来"},
    {"code": "300073", "name": "当升科技"}, {"code": "002074", "name": "国轩高科"},
    {"code": "002240", "name": "盛新锂能"}, {"code": "002056", "name": "横店东磁"},
    {"code": "002050", "name": "三花智控"}, {"code": "603806", "name": "福斯特"},
    {"code": "601865", "name": "福莱特"}, {"code": "688599", "name": "天合光能"},
    {"code": "688223", "name": "晶科能源"}, {"code": "688303", "name": "大全能源"},
    {"code": "688516", "name": "奥特维"}, {"code": "688390", "name": "固德威"},
    {"code": "688032", "name": "禾迈股份"}, {"code": "688348", "name": "昱能科技"},
    {"code": "688063", "name": "派能科技"}, {"code": "300763", "name": "锦浪科技"},
    {"code": "300724", "name": "捷佳伟创"}, {"code": "300316", "name": "晶盛机电"},
    {"code": "300118", "name": "东方日升"}, {"code": "002459", "name": "晶澳科技"},
    {"code": "002129", "name": "TCL中环"}, {"code": "000591", "name": "太阳能"},
    {"code": "600893", "name": "航发动力"}, {"code": "600760", "name": "中航沈飞"},
    {"code": "000768", "name": "中航西飞"}, {"code": "600372", "name": "中航电子"},
    {"code": "002179", "name": "中航光电"}, {"code": "600038", "name": "中直股份"},
    {"code": "600391", "name": "航发科技"}, {"code": "000738", "name": "航发控制"},
    {"code": "300696", "name": "爱乐达"}, {"code": "300775", "name": "三角防务"},
    {"code": "688122", "name": "西部超导"}, {"code": "600862", "name": "中航高科"},
    {"code": "300034", "name": "钢研高纳"}, {"code": "300855", "name": "图南股份"},
    {"code": "688333", "name": "铂力特"}, {"code": "688239", "name": "航宇科技"},
    {"code": "600702", "name": "舍得酒业"}, {"code": "000596", "name": "古井贡酒"},
    {"code": "600779", "name": "水井坊"}, {"code": "603369", "name": "今世缘"},
    {"code": "600197", "name": "伊力特"}, {"code": "000860", "name": "顺鑫农业"},
    {"code": "600559", "name": "老白干酒"}, {"code": "603198", "name": "迎驾贡酒"},
    {"code": "603589", "name": "口子窖"}, {"code": "600600", "name": "青岛啤酒"},
    {"code": "002568", "name": "百润股份"}, {"code": "002507", "name": "涪陵榨菜"},
    {"code": "300999", "name": "金龙鱼"}, {"code": "603517", "name": "绝味食品"},
    {"code": "002557", "name": "洽洽食品"}, {"code": "600132", "name": "重庆啤酒"},
    {"code": "603345", "name": "安井食品"}, {"code": "002847", "name": "盐津铺子"},
    {"code": "605499", "name": "东鹏饮料"}, {"code": "605337", "name": "李子园"},
    {"code": "600298", "name": "安琪酵母"}, {"code": "603866", "name": "桃李面包"},
    {"code": "300146", "name": "汤臣倍健"}, {"code": "603392", "name": "万泰生物"},
    {"code": "300122", "name": "智飞生物"}, {"code": "600196", "name": "复星医药"},
    {"code": "000661", "name": "长春高新"}, {"code": "300347", "name": "泰格医药"},
    {"code": "688180", "name": "君实生物"}, {"code": "688185", "name": "康希诺"},
    {"code": "688276", "name": "百克生物"}, {"code": "300896", "name": "爱美客"},
    {"code": "000538", "name": "云南白药"}, {"code": "600085", "name": "同仁堂"},
    {"code": "000963", "name": "华东医药"}, {"code": "300003", "name": "乐普医疗"},
    {"code": "300529", "name": "健帆生物"}, {"code": "002007", "name": "华兰生物"},
    {"code": "603882", "name": "金域医学"}, {"code": "300676", "name": "华大基因"},
    {"code": "688016", "name": "心脉医疗"}, {"code": "688050", "name": "爱博医疗"},
    {"code": "300033", "name": "同花顺"}, {"code": "688111", "name": "金山办公"},
    {"code": "600588", "name": "用友网络"}, {"code": "000938", "name": "紫光股份"},
    {"code": "000977", "name": "浪潮信息"}, {"code": "603019", "name": "中科曙光"},
    {"code": "600498", "name": "烽火通信"}, {"code": "300496", "name": "中科创达"},
    {"code": "300308", "name": "中际旭创"}, {"code": "002236", "name": "大华股份"},
    {"code": "002405", "name": "四维图新"}, {"code": "300339", "name": "润和软件"},
    {"code": "300454", "name": "深信服"}, {"code": "688561", "name": "奇安信"},
    {"code": "688777", "name": "中控技术"}, {"code": "300124", "name": "汇川技术"},
    {"code": "601899", "name": "紫金矿业"}, {"code": "601668", "name": "中国建筑"},
    {"code": "601669", "name": "中国电建"}, {"code": "601390", "name": "中国中铁"},
    {"code": "601800", "name": "中国交建"}, {"code": "601186", "name": "中国铁建"},
    {"code": "601618", "name": "中国中冶"}, {"code": "601117", "name": "中国化学"},
    {"code": "601868", "name": "中国能建"}, {"code": "601989", "name": "中国重工"},
    {"code": "600150", "name": "中国船舶"}, {"code": "600482", "name": "中国动力"},
    {"code": "600685", "name": "中船防务"}, {"code": "600372", "name": "中航电子"},
    {"code": "000768", "name": "中航西飞"}, {"code": "600038", "name": "中直股份"},
    {"code": "600760", "name": "中航沈飞"}, {"code": "600893", "name": "航发动力"},
    {"code": "300775", "name": "三角防务"}, {"code": "300696", "name": "爱乐达"},
    {"code": "600391", "name": "航发科技"}, {"code": "000738", "name": "航发控制"},
    {"code": "688122", "name": "西部超导"}, {"code": "600862", "name": "中航高科"},
    {"code": "300034", "name": "钢研高纳"}, {"code": "300855", "name": "图南股份"},
    {"code": "688333", "name": "铂力特"}, {"code": "688239", "name": "航宇科技"},
    {"code": "600519", "name": "贵州茅台"}, {"code": "000858", "name": "五粮液"},
    {"code": "600809", "name": "山西汾酒"}, {"code": "000568", "name": "泸州老窖"},
    {"code": "002304", "name": "洋河股份"}, {"code": "600702", "name": "舍得酒业"},
    {"code": "000596", "name": "古井贡酒"}, {"code": "600779", "name": "水井坊"},
    {"code": "603369", "name": "今世缘"}, {"code": "600197", "name": "伊力特"},
    {"code": "000860", "name": "顺鑫农业"}, {"code": "600559", "name": "老白干酒"},
    {"code": "603198", "name": "迎驾贡酒"}, {"code": "603589", "name": "口子窖"},
    {"code": "600600", "name": "青岛啤酒"}, {"code": "002568", "name": "百润股份"},
    {"code": "603288", "name": "海天味业"}, {"code": "600887", "name": "伊利股份"},
    {"code": "002507", "name": "涪陵榨菜"}, {"code": "300999", "name": "金龙鱼"},
    {"code": "603517", "name": "绝味食品"}, {"code": "002557", "name": "洽洽食品"},
    {"code": "600132", "name": "重庆啤酒"}, {"code": "603345", "name": "安井食品"},
    {"code": "002847", "name": "盐津铺子"}, {"code": "605499", "name": "东鹏饮料"},
    {"code": "605337", "name": "李子园"}, {"code": "600298", "name": "安琪酵母"},
    {"code": "603866", "name": "桃李面包"}, {"code": "300146", "name": "汤臣倍健"},
    {"code": "603392", "name": "万泰生物"}, {"code": "300122", "name": "智飞生物"},
    {"code": "600196", "name": "复星医药"}, {"code": "000661", "name": "长春高新"},
    {"code": "300347", "name": "泰格医药"}, {"code": "603259", "name": "药明康德"},
    {"code": "600276", "name": "恒瑞医药"}, {"code": "300760", "name": "迈瑞医疗"},
    {"code": "688180", "name": "君实生物"}, {"code": "688185", "name": "康希诺"},
    {"code": "688276", "name": "百克生物"}, {"code": "300896", "name": "爱美客"},
    {"code": "600436", "name": "片仔癀"}, {"code": "000538", "name": "云南白药"},
    {"code": "600085", "name": "同仁堂"}, {"code": "000963", "name": "华东医药"},
    {"code": "300003", "name": "乐普医疗"}, {"code": "300529", "name": "健帆生物"},
    {"code": "002007", "name": "华兰生物"}, {"code": "603882", "name": "金域医学"},
    {"code": "300676", "name": "华大基因"}, {"code": "688016", "name": "心脉医疗"},
    {"code": "688050", "name": "爱博医疗"}, {"code": "600570", "name": "恒生电子"},
    {"code": "300033", "name": "同花顺"}, {"code": "002230", "name": "科大讯飞"},
    {"code": "688111", "name": "金山办公"}, {"code": "600588", "name": "用友网络"},
    {"code": "002415", "name": "海康威视"}, {"code": "000938", "name": "紫光股份"},
    {"code": "000977", "name": "浪潮信息"}, {"code": "603019", "name": "中科曙光"},
    {"code": "600498", "name": "烽火通信"}, {"code": "300496", "name": "中科创达"},
    {"code": "300308", "name": "中际旭创"}, {"code": "002236", "name": "大华股份"},
    {"code": "002405", "name": "四维图新"}, {"code": "300339", "name": "润和软件"},
    {"code": "300454", "name": "深信服"}, {"code": "688561", "name": "奇安信"},
    {"code": "688777", "name": "中控技术"}, {"code": "300124", "name": "汇川技术"},
    {"code": "601899", "name": "紫金矿业"}, {"code": "601668", "name": "中国建筑"},
    {"code": "601669", "name": "中国电建"}, {"code": "601390", "name": "中国中铁"},
    {"code": "601800", "name": "中国交建"}, {"code": "601186", "name": "中国铁建"},
    {"code": "601618", "name": "中国中冶"}, {"code": "601117", "name": "中国化学"},
    {"code": "601868", "name": "中国能建"}, {"code": "601989", "name": "中国重工"},
    {"code": "600150", "name": "中国船舶"}, {"code": "600482", "name": "中国动力"},
    {"code": "600685", "name": "中船防务"},
]


class StockService:
    """股票数据服务类 - 使用腾讯实时接口 + baostock 历史接口"""

    # Baostock session 缓存
    _bs_session = None

    @classmethod
    def _ensure_bs_login(cls):
        """确保 baostock 已登录"""
        if cls._bs_session is None:
            cls._bs_session = bs.login()
        return cls._bs_session.error_code == "0"

    @staticmethod
    def _to_tencent_symbol(stock_code: str) -> str:
        """转换为腾讯接口格式: sh600519 / sz000858"""
        return ("sh" if stock_code.startswith("6") else "sz") + stock_code

    @staticmethod
    def _to_baostock_symbol(stock_code: str) -> str:
        """转换为 baostock 格式: sh.600519 / sz.000858"""
        return ("sh." if stock_code.startswith("6") else "sz.") + stock_code

    @staticmethod
    def get_realtime_data(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情数据（腾讯接口）
        """
        try:
            symbol = StockService._to_tencent_symbol(stock_code)
            url = f"http://qt.gtimg.cn/q={symbol}"
            resp = requests.get(url, timeout=10)
            resp.encoding = "gb2312"
            text = resp.text.strip()

            if not text or f"v_{symbol}=\"\"" in text:
                return None

            # 解析: v_sh600519="1~贵州茅台~600519~1770.00~1765.00~1775.00~..."
            data_str = text.split('="')[1].rstrip('"')
            parts = data_str.split("~")
            if len(parts) < 45:
                return None

            return {
                "code": stock_code,
                "name": parts[1],
                "price": float(parts[3]) if parts[3] else 0.0,
                "open": float(parts[5]) if parts[5] else 0.0,
                "high": float(parts[33]) if parts[33] else 0.0,
                "low": float(parts[34]) if parts[34] else 0.0,
                "volume": int(parts[36]) if parts[36] else 0,
                "amount": float(parts[37]) if parts[37] else 0.0,
                "change": float(parts[31]) if parts[31] else 0.0,
                "change_percent": float(parts[32]) if parts[32] else 0.0,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"获取实时数据错误: {e}")
            return None

    @staticmethod
    def get_historical_data(
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
    ) -> Optional[List[Dict]]:
        """
        获取历史K线数据（baostock 接口）
        frequency: d=日线, w=周线, m=月线
        """
        try:
            StockService._ensure_bs_login()
            symbol = StockService._to_baostock_symbol(stock_code)

            rs = bs.query_history_k_data_plus(
                symbol,
                "date,open,high,low,close,volume,amount,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag="2",  # 前复权（与主流平台保持一致）
            )

            data_list = []
            while (rs.error_code == "0") and rs.next():
                row = rs.get_row_data()
                data_list.append(
                    {
                        "date": row[0],
                        "open": float(row[1]) if row[1] else 0.0,
                        "high": float(row[2]) if row[2] else 0.0,
                        "low": float(row[3]) if row[3] else 0.0,
                        "close": float(row[4]) if row[4] else 0.0,
                        "volume": int(float(row[5])) if row[5] else 0,
                        "amount": float(row[6]) if row[6] else 0.0,
                        "change_percent": float(row[7]) if row[7] else 0.0,
                    }
                )

            return data_list
        except Exception as e:
            print(f"获取历史数据错误: {e}")
            return None

    @staticmethod
    def get_stock_info(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息（通过实时接口提取）
        """
        try:
            realtime = StockService.get_realtime_data(stock_code)
            if not realtime:
                return None

            market = "SH" if stock_code.startswith("6") else "SZ"
            return {
                "code": stock_code,
                "name": realtime["name"],
                "market": market,
                "industry": realtime["name"],
                "updated_at": datetime.now(),
            }
        except Exception as e:
            print(f"获取股票信息错误: {e}")
            return None

    @staticmethod
    def get_stock_list(keyword: Optional[str] = None) -> List[Dict[str, str]]:
        """
        获取股票列表（支持模糊匹配）
        优先从 baostock 获取，失败时使用预置列表
        """
        result = []
        try:
            StockService._ensure_bs_login()
            rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
            while (rs.error_code == "0") and rs.next():
                row = rs.get_row_data()
                code = row[0].replace("sh.", "").replace("sz.", "")
                name = row[1]
                result.append({"code": code, "name": name})
        except Exception as e:
            print(f"baostock 获取股票列表失败，使用预置列表: {e}")
            result = _POPULAR_STOCKS.copy()

        if keyword:
            keyword_lower = keyword.lower()
            result = [
                s for s in result
                if keyword_lower in s["code"].lower() or keyword_lower in s["name"].lower()
            ]
        return result[:100]

    @staticmethod
    def get_all_realtime_data() -> List[Dict[str, Any]]:
        """
        获取所有股票实时行情（用于定时任务）
        使用 baostock 全部 A 股列表 + 腾讯批量接口
        """
        try:
            StockService._ensure_bs_login()
            rs = bs.query_all_stock(day="2024-01-01")
            codes = []
            while (rs.error_code == "0") and rs.next():
                row = rs.get_row_data()
                code = row[0].replace("sh.", "sh").replace("sz.", "sz")
                codes.append(code)

            # 腾讯接口每次最多支持约 60 只，分批获取
            batch_size = 50
            result = []
            for i in range(0, min(len(codes), 200), batch_size):
                batch = codes[i : i + batch_size]
                url = f"http://qt.gtimg.cn/q={','.join(batch)}"
                resp = requests.get(url, timeout=15)
                resp.encoding = "gb2312"
                for line in resp.text.strip().split(";"):
                    line = line.strip()
                    if not line or "=\"\"" in line:
                        continue
                    parts = line.split('="')
                    if len(parts) < 2:
                        continue
                    code_raw = parts[0].replace("v_", "").replace("sh", "").replace("sz", "")
                    data = parts[1].rstrip('"').split("~")
                    if len(data) < 45:
                        continue
                    result.append(
                        {
                            "code": code_raw,
                            "name": data[1],
                            "price": float(data[3]) if data[3] else 0.0,
                            "open": float(data[5]) if data[5] else 0.0,
                            "high": float(data[33]) if data[33] else 0.0,
                            "low": float(data[34]) if data[34] else 0.0,
                            "volume": int(data[36]) if data[36] else 0,
                            "amount": float(data[37]) if data[37] else 0.0,
                            "change": float(data[31]) if data[31] else 0.0,
                            "change_percent": float(data[32]) if data[32] else 0.0,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            return result
        except Exception as e:
            print(f"获取所有实时数据错误: {e}")
            return []
