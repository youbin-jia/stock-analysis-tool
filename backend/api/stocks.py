from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from services.stock_service import StockService
from services.data_service import DataService
from services.cache_service import CacheService
from services.history_loader import (
    WARMUP_DAYS, load_history_with_warmup, resolve_period_range
)
from services.indicator_service import compute_ma, compute_macd
from models.database import get_db
from models.schemas import (
    StockInfo, StockListItem, RealtimeData,
    HistoryData
)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/realtime/{code}", response_model=RealtimeData)
def get_realtime_stock(code: str):
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
def get_stock_history(
    code: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = Query("1y", description="时间周期: 1m, 3m, 6m, 1y, all"),
    frequency: Optional[str] = Query("d", description="K线频率: d=日线, w=周线, m=月线"),
):
    """
    获取股票/场内基金历史K线数据（含 MACD 指标）
    数据来源优先级: Redis缓存 > SQLite数据库 > 东方财富/baostock 远程获取
    增量更新由定时任务负责，API层优先从本地返回，仅在本地无数据时才远程获取
    """
    if frequency not in ("d", "w", "m"):
        raise HTTPException(status_code=400, detail="frequency 仅支持 d / w / m")

    if not start or not end:
        start, end = resolve_period_range(period)

    # 1. 检查 Redis 缓存（最快路径，毫秒级）
    cached_data = CacheService.get_cached_history(code, start, end, frequency)
    if cached_data:
        import json
        return json.loads(cached_data)

    # 2. 本地/远程加载，多取一段预热数据供 MACD 收敛
    data = load_history_with_warmup(
        code, start, end, frequency, WARMUP_DAYS[frequency]
    )

    if not data:
        return []

    # 3. 在含预热段的全量上算指标，再裁剪回请求区间
    compute_macd(data)
    compute_ma(data, (5, 20, 60))
    result = [row for row in data if row["date"] >= start]

    import json
    CacheService.set_cached_history(code, start, end, frequency, json.dumps(result))
    return result


@router.get("/info/{code}", response_model=StockInfo)
def get_stock_info(code: str):
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
def get_stock_list(keyword: Optional[str] = Query(None, description="搜索关键词")):
    """获取股票列表"""
    return StockService.get_stock_list(keyword)


@router.get("/search", response_model=List[StockListItem])
def search_stocks(keyword: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索股票"""
    return StockService.get_stock_list(keyword)


@router.get("/batch-realtime")
def get_batch_realtime(codes: str = Query(..., description="股票代码，逗号分隔")):
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
