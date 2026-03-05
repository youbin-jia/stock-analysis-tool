import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class StockService:
    """股票数据服务类"""

    @staticmethod
    def get_realtime_data(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情数据

        Args:
            stock_code: 股票代码，如 600519

        Returns:
            实时行情数据字典
        """
        try:
            # 获取所有A股实时行情
            df = ak.stock_zh_a_spot_em()

            # 查找指定股票
            stock_df = df[df['代码'] == stock_code]

            if stock_df.empty:
                return None

            row = stock_df.iloc[0]

            return {
                'code': str(row['代码']),
                'name': str(row['名称']),
                'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                'open': float(row['今开']) if pd.notna(row['今开']) else 0,
                'high': float(row['最高']) if pd.notna(row['最高']) else 0,
                'low': float(row['最低']) if pd.notna(row['最低']) else 0,
                'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0,
                'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取实时数据错误: {e}")
            return None

    @staticmethod
    def get_historical_data(stock_code: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """
        获取历史K线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD

        Returns:
            历史K线数据列表
        """
        try:
            # 判断市场
            if stock_code.startswith('6'):
                symbol = stock_code + '.SH'
            else:
                symbol = stock_code + '.SZ'

            # 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust=""
            )

            if df.empty:
                return []

            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_percent'
            })

            # 转换为字典列表
            result = []
            for _, row in df.iterrows():
                result.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'open': float(row['open']) if pd.notna(row['open']) else 0,
                    'close': float(row['close']) if pd.notna(row['close']) else 0,
                    'high': float(row['high']) if pd.notna(row['high']) else 0,
                    'low': float(row['low']) if pd.notna(row['low']) else 0,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                    'amount': float(row['amount']) if pd.notna(row['amount']) else 0,
                    'change_percent': float(row['change_percent']) if pd.notna(row['change_percent']) else 0
                })

            return result
        except Exception as e:
            print(f"获取历史数据错误: {e}")
            return None

    @staticmethod
    def get_stock_list(keyword: Optional[str] = None) -> List[Dict[str, str]]:
        """
        获取股票列表

        Args:
            keyword: 搜索关键词（股票名称或代码）

        Returns:
            股票列表
        """
        try:
            df = ak.stock_zh_a_spot_em()

            # 过滤列
            df = df[['代码', '名称']].copy()

            if keyword:
                df = df[
                    df['代码'].str.contains(keyword, case=False) |
                    df['名称'].str.contains(keyword, case=False)
                ]

            # 限制返回数量
            df = df.head(100)

            result = []
            for _, row in df.iterrows():
                result.append({
                    'code': str(row['代码']),
                    'name': str(row['名称'])
                })

            return result
        except Exception as e:
            print(f"获取股票列表错误: {e}")
            return []

    @staticmethod
    def get_stock_info(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票基本信息
        """
        try:
            # 判断市场
            if stock_code.startswith('6'):
                symbol = stock_code + '.SH'
                market = 'SH'
            else:
                symbol = stock_code + '.SZ'
                market = 'SZ'

            # 获取基本信息
            df = ak.stock_zh_a_spot_em()
            stock_df = df[df['代码'] == stock_code]

            if stock_df.empty:
                return None

            row = stock_df.iloc[0]

            return {
                'code': str(row['代码']),
                'name': str(row['名称']),
                'market': market,
                'industry': str(row['名称']),  # akshare 可能没有行业信息，先用名称
                'updated_at': datetime.now()
            }
        except Exception as e:
            print(f"获取股票信息错误: {e}")
            return None

    @staticmethod
    def get_all_realtime_data() -> List[Dict[str, Any]]:
        """
        获取所有股票实时行情（用于定时任务）

        Returns:
            所有股票的实时数据列表
        """
        try:
            df = ak.stock_zh_a_spot_em()

            # 选择需要的列
            df = df[['代码', '名称', '最新价', '今开', '最高', '最低', '成交量', '成交额', '涨跌额', '涨跌幅']]

            result = []
            for _, row in df.iterrows():
                result.append({
                    'code': str(row['代码']),
                    'name': str(row['名称']),
                    'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    'open': float(row['今开']) if pd.notna(row['今开']) else 0,
                    'high': float(row['最高']) if pd.notna(row['最高']) else 0,
                    'low': float(row['最低']) if pd.notna(row['最低']) else 0,
                    'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                    'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0,
                    'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                    'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                    'timestamp': datetime.now().isoformat()
                })

            return result
        except Exception as e:
            print(f"获取所有实时数据错误: {e}")
            return []
