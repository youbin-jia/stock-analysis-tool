from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import json
from services.sector_service import SectorService
from services.cache_service import CacheService
from models.schemas import SectorInfo, SectorFundItem

router = APIRouter(prefix="/api/sectors", tags=["sectors"])


@router.get("/industry", response_model=List[SectorInfo])
async def get_industry_sectors(
    sort_by: str = Query("daily", description="排序方式: daily(日涨幅), 5day, month, 3month, year"),
):
    """获取行业板块列表"""
    cache_key = f"industry:{sort_by}"
    cached = CacheService.get_cached_sectors(cache_key)
    if cached:
        return json.loads(cached)

    data = SectorService.get_industry_sectors(sort_by=sort_by)

    if data:
        CacheService.set_cached_sectors(cache_key, json.dumps(data))

    return data


@router.get("/concept", response_model=List[SectorInfo])
async def get_concept_sectors(
    sort_by: str = Query("daily", description="排序方式: daily(日涨幅), 5day, month, 3month, year"),
):
    """获取概念板块列表"""
    cache_key = f"concept:{sort_by}"
    cached = CacheService.get_cached_sectors(cache_key)
    if cached:
        return json.loads(cached)

    data = SectorService.get_concept_sectors(sort_by=sort_by)

    if data:
        CacheService.set_cached_sectors(cache_key, json.dumps(data))

    return data


@router.get("/funds", response_model=List[SectorFundItem])
async def get_funds_by_type(
    fund_type: str = Query("全部", description="基金类型: 全部, 股票型, 混合型, 债券型, 指数型, QDII, FOF"),
    sort_by: str = Query("daily", description="排序方式: daily(日涨幅), week, month, 3month, 6month, year, total"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
):
    """按基金类型筛选并按涨幅排序"""
    cached = CacheService.get_cached_fund_rank(fund_type, sort_by)
    if cached:
        return json.loads(cached)

    data = SectorService.get_funds_by_type(fund_type=fund_type, sort_by=sort_by, limit=limit)

    if data:
        CacheService.set_cached_fund_rank(fund_type, sort_by, json.dumps(data))

    return data
