from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from services.quant_service import QuantService
from models.schemas import (
    FundamentalFilter, MarketValuation,
)

router = APIRouter(prefix="/api/quant", tags=["quant"])


@router.get("/screen")
async def smart_screen(type: str = Query("cxg", description="选股类型: cxg/cxd/cxfl/cxsl/ljqs/ljqd/lxsz/lxxd/xstp/xxtp/xzjp")):
    """智能选股 - 技术面+市场面筛选"""
    data = QuantService.get_smart_screen(type)
    if not data:
        return []
    return data


@router.get("/hot-stocks")
async def hot_stocks():
    """东方财富人气榜"""
    data = QuantService.get_hot_stocks()
    if not data:
        return []
    return data


@router.get("/market-valuation", response_model=MarketValuation)
async def market_valuation():
    """全市场估值统计"""
    data = QuantService.get_market_valuation()
    if not data:
        raise HTTPException(status_code=404, detail="市场估值数据不可用")
    return data


@router.post("/fundamental-screen")
async def fundamental_screen(filters: FundamentalFilter):
    """多因子选股 - 基本面筛选"""
    data = QuantService.get_stock_fundamental_screen(filters.model_dump(exclude_none=True))
    return data


@router.get("/score/{code}")
async def stock_score(code: str):
    """单只股票综合评分"""
    data = QuantService.get_stock_score(code)
    if not data:
        raise HTTPException(status_code=404, detail="股票评分数据不可用")
    return data


@router.get("/recommend")
async def stock_recommendation(limit: int = Query(20, ge=1, le=100, description="推荐数量")):
    """综合评分排行"""
    data = QuantService.get_stock_recommendation(limit)
    return data


@router.get("/fund-recommend")
async def fund_recommend(
    type: str = Query("全部", description="基金类型: 全部/股票型/混合型/债券型/指数型/QDII/FOF"),
    limit: int = Query(20, ge=1, le=100, description="推荐数量"),
):
    """基金智能推荐"""
    data = QuantService.get_fund_recommend(type, limit)
    return data
