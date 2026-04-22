from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database import get_db, StockHistory, Stock, Fund, FundHistory
from services.stock_service import StockService


class DataService:
    """数据处理服务类"""

    @staticmethod
    def save_to_database(stock_code: str, data: List[Dict[str, Any]], frequency: str = "d"):
        """
        保存历史数据到数据库（支持日/周/月）
        """
        db = next(get_db())
        try:
            for item in data:
                trade_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

                existing = db.query(StockHistory).filter(
                    and_(
                        StockHistory.stock_code == stock_code,
                        StockHistory.trade_date == trade_date,
                        StockHistory.frequency == frequency,
                    )
                ).first()

                if existing:
                    existing.open_price = item['open']
                    existing.close_price = item['close']
                    existing.high_price = item['high']
                    existing.low_price = item['low']
                    existing.volume = item['volume']
                    existing.amount = item['amount']
                    existing.change_percent = item['change_percent']
                    existing.updated_at = datetime.now()
                else:
                    history = StockHistory(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        frequency=frequency,
                        open_price=item['open'],
                        close_price=item['close'],
                        high_price=item['high'],
                        low_price=item['low'],
                        volume=item['volume'],
                        amount=item['amount'],
                        change_percent=item['change_percent'],
                        updated_at=datetime.now(),
                    )
                    db.add(history)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存数据库错误: {e}")
        finally:
            db.close()

    @staticmethod
    def load_from_database(stock_code: str, start_date: str, end_date: str, frequency: str = "d") -> List[Dict[str, Any]]:
        """
        从数据库加载历史数据
        """
        db = next(get_db())
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

            records = db.query(StockHistory).filter(
                and_(
                    StockHistory.stock_code == stock_code,
                    StockHistory.frequency == frequency,
                    StockHistory.trade_date >= start,
                    StockHistory.trade_date <= end,
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
                    'change_percent': record.change_percent,
                })

            return result
        except Exception as e:
            print(f"从数据库加载数据错误: {e}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_latest_date_in_db(stock_code: str, frequency: str = "d") -> date:
        """
        获取数据库中某股票的最新交易日期
        """
        db = next(get_db())
        try:
            record = db.query(StockHistory).filter(
                StockHistory.stock_code == stock_code,
                StockHistory.frequency == frequency,
            ).order_by(StockHistory.trade_date.desc()).first()

            if record:
                return record.trade_date
            return None
        finally:
            db.close()

    @staticmethod
    def get_earliest_date_in_db(stock_code: str, frequency: str = "d") -> date:
        """
        获取数据库中某股票的最早交易日期
        """
        db = next(get_db())
        try:
            record = db.query(StockHistory).filter(
                StockHistory.stock_code == stock_code,
                StockHistory.frequency == frequency,
            ).order_by(StockHistory.trade_date.asc()).first()

            if record:
                return record.trade_date
            return None
        finally:
            db.close()

    @staticmethod
    def save_stock_info(stock_code: str, info: Dict[str, Any]):
        """
        保存股票基本信息到数据库
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
                    created_at=datetime.now(),
                )
                db.add(stock)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存股票信息错误: {e}")
        finally:
            db.close()

    @staticmethod
    def _align_comparison_data(all_data: Dict[str, List[Dict]], price_key: str,
                               normalize: bool = True) -> Dict[str, Any]:
        """
        对齐多资产对比数据：
        1. 以最晚的起始日期为共同起点
        2. 以最早的结束日期为共同终点（或取最大日期前向填充）
        3. 统一日期轴，缺失值前向填充
        """
        if not all_data:
            return {'items': [], 'dates': []}

        # 找共同起始 = 最晚的第一条日期；共同结束 = 最早的最新日期（确保都有数据）
        common_start = None
        common_end = None
        for data in all_data.values():
            if data:
                first = data[0]['date']
                last = data[-1]['date']
                if common_start is None or first > common_start:
                    common_start = first
                if common_end is None or last < common_end:
                    common_end = last

        # 若某只资产在 common_end 之后还有数据，保留到它自己的最新日期
        max_end = None
        for data in all_data.values():
            if data:
                last = data[-1]['date']
                if max_end is None or last > max_end:
                    max_end = last

        # 收集所有在 [common_start, max_end] 区间内的日期并排序
        date_set = set()
        for data in all_data.values():
            if data:
                filtered = [item for item in data if item['date'] >= common_start]
                for item in filtered:
                    date_set.add(item['date'])
        sorted_dates = sorted(date_set)

        # 对齐每只资产的数据
        aligned_items = []
        for code, data in all_data.items():
            # 建立 date -> price 映射
            price_map = {}
            for item in data:
                price_map[item['date']] = item[price_key]

            aligned_values = []
            last_val = None
            for d in sorted_dates:
                if d in price_map:
                    last_val = price_map[d]
                    aligned_values.append({'date': d, 'value': last_val})
                elif last_val is not None:
                    # 前向填充（交易停牌等导致缺失）
                    aligned_values.append({'date': d, 'value': last_val})
                else:
                    # 在资产成立前，用 null 占位（图表会断开）
                    aligned_values.append({'date': d, 'value': None})

            # 截断到 common_end 之前的 null，避免前端出现大量空数据拖慢渲染
            # 保留从第一个有效值开始到 max_end
            first_valid = next((i for i, v in enumerate(aligned_values)
                                if v['value'] is not None), None)
            if first_valid is not None:
                aligned_values = aligned_values[first_valid:]
                # 重新截取 sorted_dates 与之对应
                aligned_dates = sorted_dates[first_valid:]
            else:
                aligned_dates = sorted_dates

            if normalize and aligned_values:
                first_price = aligned_values[0]['value']
                if first_price and first_price != 0:
                    for v in aligned_values:
                        if v['value'] is not None:
                            v['value'] = round((v['value'] - first_price) / first_price * 100, 2)
            elif not normalize:
                for v in aligned_values:
                    if v['value'] is not None:
                        v['value'] = round(v['value'], 2)

            aligned_items.append({
                'code': code,
                'data': aligned_values,
                'dates': aligned_dates,
            })

        # 取交集日期（所有资产都有值的日期）作为最终统一日期轴，保证图表完全对齐
        # 若只有一只资产，保留其完整日期
        if len(aligned_items) == 1:
            final_dates = aligned_items[0]['dates']
        else:
            # 找所有资产都有有效值的日期
            valid_date_sets = []
            for item in aligned_items:
                valid_dates = {v['date'] for v in item['data'] if v['value'] is not None}
                valid_date_sets.append(valid_dates)
            common_dates = valid_date_sets[0].intersection(*valid_date_sets[1:])
            final_dates = sorted(common_dates)

        return {'items': aligned_items, 'dates': final_dates}

    @staticmethod
    def compare_stocks(stock_codes: List[str], start_date: str, end_date: str,
                      normalize: bool = True, frequency: str = "d") -> Dict[str, Any]:
        """
        多股票对比数据准备（对齐到最晚起始日期）
        """
        all_data = {}
        for code in stock_codes:
            data = DataService.load_from_database(code, start_date, end_date, frequency)

            if not data or len(data) < 10:
                api_data = StockService.get_historical_data(code, start_date, end_date, frequency)
                if api_data:
                    data = api_data
                    DataService.save_to_database(code, data, frequency)

            if data:
                all_data[code] = data

        aligned = DataService._align_comparison_data(all_data, 'close', normalize)
        result = {'stocks': [], 'dates': aligned['dates']}

        for item in aligned['items']:
            code = item['code']
            stock_info = StockService.get_stock_info(code)
            name = stock_info['name'] if stock_info else code

            # 过滤到共同日期
            common_dates = set(result['dates'])
            filtered_data = [v for v in item['data'] if v['date'] in common_dates]
            result['stocks'].append({
                'code': code,
                'name': name,
                'data': filtered_data,
            })

        return result

    # ========== 基金数据处理 ==========

    @staticmethod
    def save_fund_to_database(fund_code: str, data: List[Dict[str, Any]]):
        """
        保存基金历史净值到数据库
        """
        db = next(get_db())
        try:
            for item in data:
                trade_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

                existing = db.query(FundHistory).filter(
                    and_(
                        FundHistory.fund_code == fund_code,
                        FundHistory.trade_date == trade_date,
                    )
                ).first()

                if existing:
                    existing.nav = item['nav']
                    existing.adjusted_nav = item.get('adjusted_nav')
                    existing.change_percent = item.get('change_percent', 0)
                    existing.updated_at = datetime.now()
                else:
                    history = FundHistory(
                        fund_code=fund_code,
                        trade_date=trade_date,
                        nav=item['nav'],
                        adjusted_nav=item.get('adjusted_nav'),
                        change_percent=item.get('change_percent', 0),
                        updated_at=datetime.now(),
                    )
                    db.add(history)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存基金数据库错误: {e}")
        finally:
            db.close()

    @staticmethod
    def load_fund_from_database(fund_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        从数据库加载基金历史净值（优先使用复权净值）
        """
        db = next(get_db())
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

            records = db.query(FundHistory).filter(
                and_(
                    FundHistory.fund_code == fund_code,
                    FundHistory.trade_date >= start,
                    FundHistory.trade_date <= end,
                )
            ).order_by(FundHistory.trade_date).all()

            result = []
            for record in records:
                # 优先使用复权净值，缺失则回退到单位净值
                use_nav = record.adjusted_nav if record.adjusted_nav is not None else record.nav
                result.append({
                    'date': record.trade_date.strftime('%Y-%m-%d'),
                    'nav': record.nav,
                    'adjusted_nav': use_nav,
                    'change_percent': record.change_percent,
                })
            return result
        except Exception as e:
            print(f"从数据库加载基金数据错误: {e}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_fund_latest_date_in_db(fund_code: str) -> date:
        """
        获取数据库中某基金的最新净值日期
        """
        db = next(get_db())
        try:
            record = db.query(FundHistory).filter(
                FundHistory.fund_code == fund_code,
            ).order_by(FundHistory.trade_date.desc()).first()

            if record:
                return record.trade_date
            return None
        finally:
            db.close()

    @staticmethod
    def save_fund_info(fund_code: str, info: Dict[str, Any]):
        """
        保存基金基本信息到数据库
        """
        db = next(get_db())
        try:
            existing = db.query(Fund).filter(Fund.code == fund_code).first()

            if existing:
                existing.name = info.get('name')
                existing.fund_type = info.get('type')
            else:
                fund = Fund(
                    code=fund_code,
                    name=info.get('name'),
                    fund_type=info.get('type'),
                    created_at=datetime.now(),
                )
                db.add(fund)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存基金信息错误: {e}")
        finally:
            db.close()

    @staticmethod
    def compare_funds(fund_codes: List[str], start_date: str, end_date: str,
                      normalize: bool = True, fetch_full: bool = False) -> Dict[str, Any]:
        """
        多基金对比数据准备（对齐到最晚起始日期）
        """
        all_data = {}
        for code in fund_codes:
            if fetch_full:
                # 强制获取全部历史数据（用于 period=all）
                from services.fund_service import FundService
                api_data = FundService.get_fund_history(code, None, None)
                if api_data:
                    DataService.save_fund_to_database(code, api_data)
                    all_data[code] = api_data
                continue

            data = DataService.load_fund_from_database(code, start_date, end_date)

            if not data or len(data) < 5:
                from services.fund_service import FundService
                api_data = FundService.get_fund_history(code, start_date, end_date)
                if api_data:
                    data = api_data
                    DataService.save_fund_to_database(code, data)

            if data:
                all_data[code] = data

        aligned = DataService._align_comparison_data(all_data, 'adjusted_nav', normalize)
        result = {'funds': [], 'dates': aligned['dates']}

        for item in aligned['items']:
            code = item['code']
            from services.fund_service import FundService
            fund_info = FundService.get_fund_info(code)
            name = fund_info['name'] if fund_info else code

            common_dates = set(result['dates'])
            filtered_data = [v for v in item['data'] if v['date'] in common_dates]
            result['funds'].append({
                'code': code,
                'name': name,
                'data': filtered_data,
            })

        return result
