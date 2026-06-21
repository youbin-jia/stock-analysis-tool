from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from services.quant_service import QuantService
from services.style_scoring import (
    score_all_styles, interpret_market_valuation, STYLES,
)
from services.bulk_scan_service import (
    start_scan_async, get_scan_state, get_all_style_tops, get_style_top,
)
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
    """单只股票综合评分（含多流派分析）"""
    data = QuantService.get_stock_score(code)
    if not data:
        raise HTTPException(status_code=404, detail="股票评分数据不可用")
    # 附加流派评分
    style_result = score_all_styles(data)
    data["style_analysis"] = style_result
    return data


@router.get("/styles")
async def list_styles():
    """获取所有投资流派定义（用于前端展示流派卡片）"""
    return [
        {"key": k, **v} for k, v in STYLES.items()
    ]


@router.get("/style-score/{code}")
async def style_score(code: str):
    """单只股票的多流派评分详情"""
    data = QuantService.get_stock_score(code)
    if not data:
        raise HTTPException(status_code=404, detail="股票数据不可用")
    return {
        "code": data.get("code"),
        "name": data.get("name"),
        "fundamental": {
            "pe_ttm": data.get("pe_ttm"),
            "pb": data.get("pb"),
            "roe": data.get("roe"),
            "net_profit_margin": data.get("net_profit_margin"),
            "revenue_growth": data.get("revenue_growth"),
            "net_profit_growth": data.get("net_profit_growth"),
            "debt_ratio": data.get("debt_ratio"),
            "dividend_yield": data.get("dividend_yield"),
        },
        **score_all_styles(data),
    }


@router.get("/market-cycle")
async def market_cycle():
    """市场周期解读 —— 基于席勒/马克斯的周期思想"""
    market = QuantService.get_market_valuation()
    if not market:
        raise HTTPException(status_code=404, detail="市场数据不可用")
    return {
        "market": market,
        "interpretation": interpret_market_valuation(market),
    }


# ===== 全市场流派 Top 扫描 =====

@router.post("/bulk-scan/start")
async def bulk_scan_start(max_candidates: int = Query(800, ge=100, le=2000)):
    """触发全市场扫描（异步），返回是否成功启动"""
    started = start_scan_async(max_candidates)
    return {"started": started, "state": get_scan_state()}


@router.get("/bulk-scan/state")
async def bulk_scan_state():
    """查询扫描进度"""
    return get_scan_state()


@router.get("/style-tops")
async def style_tops(limit: int = Query(10, ge=1, le=50)):
    """获取 4 流派各自 Top N（来自最近一次扫描结果）"""
    return get_all_style_tops(limit)


@router.get("/style-top/{style_key}")
async def style_top(style_key: str, limit: int = Query(10, ge=1, le=50)):
    """获取指定流派 Top N"""
    if style_key not in STYLES:
        raise HTTPException(status_code=404, detail="未知流派")
    return get_style_top(style_key, limit)


@router.get("/recommend")
async def stock_recommendation(
    limit: int = Query(20, ge=1, le=100, description="推荐数量"),
    style: Optional[str] = Query(None, description="按流派排序: graham_deep_value/buffett_quality/lynch_growth/marks_defensive"),
):
    """综合评分排行（含流派分析，支持按流派排序）"""
    data = QuantService.get_stock_recommendation(limit if not style else 100)
    # 附加流派评分
    enriched = []
    for d in data:
        s = score_all_styles(d)
        d["composite_score"] = s["composite_score"]
        d["best_style"] = s["best_style"]
        d["style_scores"] = {
            item["key"]: {"score": item["score"], "passed_count": item["passed_count"], "total_rules": item["total_rules"]}
            for item in s["styles"]
        }
        enriched.append(d)
    if style and style in STYLES:
        enriched.sort(key=lambda x: x["style_scores"].get(style, {}).get("score", 0), reverse=True)
        enriched = enriched[:limit]
    return enriched


@router.get("/fund-recommend")
async def fund_recommend(
    type: str = Query("全部", description="基金类型: 全部/股票型/混合型/债券型/指数型/QDII/FOF"),
    limit: int = Query(20, ge=1, le=100, description="推荐数量"),
):
    """基金智能推荐"""
    data = QuantService.get_fund_recommend(type, limit)
    return data
