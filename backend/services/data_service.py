from typing import List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database import get_db, StockHistory, Stock
from services.stock_service import StockService


class DataService:
    """数据处理服务类"""

    @staticmethod
    def normalize_data(raw_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        数据格式标准化

        Args:
            raw_data: 原始数据

        Returns:
            标准化后的数据
        """
        return raw_data

    @staticmethod
    def save_to_database(stock_code: str, data: List[Dict[str, Any]]):
        """
        保存历史数据到数据库

        Args:
            stock_code: 股票代码
            data: 历史数据列表
        """
        db = next(get_db())
        try:
            for item in data:
                trade_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

                # 检查是否已存在
                existing = db.query(StockHistory).filter(
                    and_(
                        StockHistory.stock_code == stock_code,
                        StockHistory.trade_date == trade_date
                    )
                ).first()

                if existing:
                    # 更新
                    existing.open_price = item['open']
                    existing.close_price = item['close']
                    existing.high_price = item['high']
                    existing.low_price = item['low']
                    existing.volume = item['volume']
                    existing.amount = item['amount']
                    existing.change_percent = item['change_percent']
                    existing.updated_at = datetime.now()
                else:
                    # 插入新记录
                    history = StockHistory(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        open_price=item['open'],
                        close_price=item['close'],
                        high_price=item['high'],
                        low_price=item['low'],
                        volume=item['volume'],
                        amount=item['amount'],
                        change_percent=item['change_percent'],
                        updated_at=datetime.now()
                    )
                    db.add(history)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存数据库错误: {e}")
        finally:
            db.close()

    @staticmethod
    def load_from_database(stock_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        从数据库加载历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            历史数据列表
        """
        db = next(get_db())
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

            records = db.query(StockHistory).filter(
                and_(
                    StockHistory.stock_code == stock_code,
                    StockHistory.trade_date >= start,
                    StockHistory.trade_date <= end
                )
            ).order_by(StockHistory.trade_date).all()

            result = []
            for record in records:
                result.append({
                    'date': record.trade_date.strftime('%Y-%m-%d'),
                    'open': record.open_price,
                    'close': record.close_price,
                    'high': record.high_price,
                    'low': record.low_price,
                    'volume': record.volume,
                    'amount': record.amount,
                    'change_percent': record.change_percent
                })

            return result
        except Exception as e:
            print(f"从数据库加载数据错误: {e}")
            return []
        finally:
            db.close()

    @staticmethod
    def save_stock_info(stock_code: str, info: Dict[str, Any]):
        """
        保存股票基本信息到数据库

        Args:
            stock_code: 股票代码
            info: 股票信息字典
        """
        db = next(get_db())
        try:
            existing = db.query(Stock).filter(Stock.code == stock_code).first()

            if existing:
                existing.name = info.get('name')
                existing.industry = info.get('industry')
                existing.market = info.get('market')
            else:
                stock = Stock(
                    code=stock_code,
                    name=info.get('name'),
                    industry=info.get('industry'),
                    market=info.get('market'),
                    created_at=datetime.now()
                )
                db.add(stock)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存股票信息错误: {e}")
        finally:
            db.close()

    @staticmethod
    def compare_stocks(stock_codes: List[str], start_date: str, end_date: str,
                      normalize: bool = True) -> Dict[str, Any]:
        """
        多股票对比数据准备

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            normalize: 是否归一化（计算收益率）

        Returns:
            对比数据
        """
        result = {'stocks': [], 'dates': []}

        # 获取所有股票的数据
        all_data = {}
        for code in stock_codes:
            # 先从数据库加载
            data = DataService.load_from_database(code, start_date, end_date)

            # 如果数据不全，从API获取
            if not data or len(data) < 10:
                api_data = StockService.get_historical_data(code, start_date, end_date)
                if api_data:
                    data = api_data
                    DataService.save_to_database(code, data)

            if data:
                all_data[code] = data

        # 获取日期列表（以第一只股票的日期为基准）
        if all_data:
            result['dates'] = [item['date'] for item in list(all_data.values())[0]]

        # 准备对比数据
        for code, data in all_data.items():
            stock_info = StockService.get_stock_info(code)
            name = stock_info['name'] if stock_info else code

            if normalize and data:
                # 计算收益率（以第一个交易日收盘价为基准）
                base_price = data[0]['close']
                normalized_data = []
                for item in data:
                    return_rate = (item['close'] - base_price) / base_price * 100
                    normalized_data.append({
                        'date': item['date'],
                        'value': round(return_rate, 2)
                    })
                result['stocks'].append({
                    'code': code,
                    'name': name,
                    'data': normalized_data
                })
            else:
                # 使用原始价格
                result['stocks'].append({
                    'code': code,
                    'name': name,
                    'data': [{'date': item['date'], 'value': item['close']} for item in data]
                })

        return result

    @staticmethod
    def get_latest_date_in_db(stock_code: str) -> date:
        """
        获取数据库中某股票的最新交易日期

        Args:
            stock_code: 股票代码

        Returns:
            最新交易日期
        """
        db = next(get_db())
        try:
            record = db.query(StockHistory).filter(
                StockHistory.stock_code == stock_code
            ).order_by(StockHistory.trade_date.desc()).first()

            if record:
                return record.trade_date
            return None
        finally:
            db.close()
