from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from services.stock_service import StockService
from services.data_service import DataService
from services.cache_service import CacheService
from models.database import get_db
from models.schemas import (
    StockInfo, StockListItem, RealtimeData,
    HistoryData
)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/realtime/{code}", response_model=RealtimeData)
async def get_realtime_stock(code: str):
    """获取单只股票实时行情"""
    cached_data = CacheService.get_cached_realtime(code)
    if cached_data:
        return cached_data

    data = StockService.get_realtime_data(code)
    if not data:
        raise HTTPException(status_code=404, detail="Stock not found")

    CacheService.set_cached_realtime(code, data)

    stock_info = StockService.get_stock_info(code)
    if stock_info:
        DataService.save_stock_info(code, stock_info)

    return data


@router.get("/history/{code}")
async def get_stock_history(
    code: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = Query("1y", description="时间周期: 1m, 3m, 6m, 1y, all"),
    frequency: Optional[str] = Query("d", description="K线频率: d=日线, w=周线, m=月线"),
):
    """
    获取股票历史K线数据
    优先从本地数据库读取，缺失部分从 baostock 增量补充
    """
    if not start or not end:
        end_date = datetime.now()
        if period == "1m":
            start_date = end_date - timedelta(days=30)
        elif period == "3m":
            start_date = end_date - timedelta(days=90)
        elif period == "6m":
            start_date = end_date - timedelta(days=180)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = end_date - timedelta(days=3650)

        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")

    # 检查缓存
    cached_data = CacheService.get_cached_history(code, start, end, frequency)
    if cached_data:
        import json
        return json.loads(cached_data)

    # 从数据库加载
    db_data = DataService.load_from_database(code, start, end, frequency)

    # 如果数据库数据不够，检查是否需要增量补充
    if not db_data or len(db_data) < 5:
        # 尝试获取全部历史数据并缓存
        api_data = StockService.get_historical_data(code, start, end, frequency)
        if api_data:
            db_data = api_data
            DataService.save_to_database(code, db_data, frequency)
    else:
        # 增量更新：检查数据库最新日期到 end 之间是否有缺失
        latest_date = DataService.get_latest_date_in_db(code, frequency)
        if latest_date:
            latest_str = latest_date.strftime("%Y-%m-%d")
            if latest_str < end:
                # 从最新日期的下一天开始补充
                next_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                api_data = StockService.get_historical_data(code, next_date, end, frequency)
                if api_data:
                    DataService.save_to_database(code, api_data, frequency)
                    # 重新加载完整数据
                    db_data = DataService.load_from_database(code, start, end, frequency)

    # 缓存数据
    if db_data:
        import json
        CacheService.set_cached_history(code, start, end, frequency, json.dumps(db_data))

    return db_data or []


@router.get("/info/{code}", response_model=StockInfo)
async def get_stock_info(code: str):
    """获取股票基本信息"""
    db = next(get_db())
    try:
        from models.database import Stock
        stock = db.query(Stock).filter(Stock.code == code).first()
        if stock:
            return StockInfo(
                code=stock.code,
                name=stock.name,
                industry=stock.industry,
                market=stock.market
            )
    finally:
        db.close()

    api_info = StockService.get_stock_info(code)
    if not api_info:
        raise HTTPException(status_code=404, detail="Stock not found")

    DataService.save_stock_info(code, api_info)

    return StockInfo(
        code=api_info['code'],
        name=api_info['name'],
        industry=api_info.get('industry'),
        market=api_info.get('market')
    )


@router.get("/list", response_model=List[StockListItem])
async def get_stock_list(keyword: Optional[str] = Query(None, description="搜索关键词")):
    """获取股票列表"""
    return StockService.get_stock_list(keyword)


@router.get("/search", response_model=List[StockListItem])
async def search_stocks(keyword: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索股票"""
    return StockService.get_stock_list(keyword)


@router.get("/batch-realtime")
async def get_batch_realtime(codes: str = Query(..., description="股票代码，逗号分隔")):
    """批量获取实时行情"""
    code_list = [c.strip() for c in codes.split(',')]
    result = []

    for code in code_list:
        cached_data = CacheService.get_cached_realtime(code)
        if cached_data:
            result.append(cached_data)
        else:
            data = StockService.get_realtime_data(code)
            if data:
                CacheService.set_cached_realtime(code, data)
                result.append(data)

    return result
