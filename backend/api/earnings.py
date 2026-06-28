from fastapi import APIRouter, HTTPException
from services.earnings_service import build_earnings_snapshot, fetch_financial_summary

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/{code}")
async def earnings_snapshot(code: str):
    """财报快评（draft）

    返回结构化的最新业绩点评，包含同比/环比、多期趋势、
    自动识别的 red flags 和人工复核提示。
    """
    snapshot = build_earnings_snapshot(code)
    if not snapshot.get("available"):
        raise HTTPException(status_code=404, detail=snapshot.get("message", "未获取到财务数据"))
    return snapshot


@router.get("/{code}/history")
async def earnings_history(code: str, limit: int = 8):
    """最近 N 期财务摘要"""
    data = fetch_financial_summary(code, limit=limit)
    return {"code": code, "count": len(data), "data": data}
