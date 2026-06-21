from fastapi import APIRouter, Query, HTTPException
from services.policy_service import (
    start_collect_async, get_scan_state, get_collect_result,
)

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.post("/refresh")
async def refresh_policy(
    days: int = Query(30, ge=1, le=90, description="最近 N 天"),
    max_articles: int = Query(40, ge=10, le=80, description="最多分析文章数"),
):
    """一键刷新：抓取近 N 天政策文章并 AI 总结（异步）"""
    started = start_collect_async(days=days, max_articles=max_articles)
    return {"started": started, "state": get_scan_state()}


@router.get("/state")
async def policy_state():
    """查询刷新进度"""
    return get_scan_state()


@router.get("/result")
async def policy_result():
    """获取最近一次刷新的结果"""
    data = get_collect_result()
    if not data:
        return {"available": False}
    return {"available": True, **data}
