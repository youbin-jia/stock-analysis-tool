from fastapi import APIRouter, HTTPException, Query

from services.cache_service import CacheService
from services.scenario_service import INDEX_MAP, ScenarioService

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/indexes")
async def list_indexes():
    """可选指数列表"""
    return [{"code": code, "name": name} for code, name in INDEX_MAP.items()]


@router.get("/scenario")
async def get_index_scenario(
    index_code: str = Query("sh000688", description="指数代码，如 sh000688"),
    forward_days: int = Query(42, ge=5, le=120, description="向前推演的交易日数"),
    vol_window: int = Query(60, ge=20, le=250, description="已实现波动率的回看窗口"),
):
    """指数前瞻情景区间（基于历史波动率的分位数锥，非预测）"""
    cache_key = f"scenario:{index_code}:{forward_days}:{vol_window}"
    cached = CacheService.get_cached_quant(cache_key)
    if cached:
        return cached

    data = ScenarioService.get_scenario(
        index_code=index_code, forward_days=forward_days, vol_window=vol_window
    )
    if not data:
        raise HTTPException(status_code=404, detail="指数数据获取失败")

    CacheService.set_cached_quant(cache_key, data, ttl=1800)
    return data
