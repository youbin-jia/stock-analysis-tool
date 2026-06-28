from fastapi import APIRouter, Query
from services.calendar_service import upcoming_calendar, stock_calendar

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/upcoming")
async def get_upcoming(days: int = Query(30, ge=1, le=90)):
    """全市场未来 N 天催化剂（财报/分红/解禁）"""
    return upcoming_calendar(days_ahead=days)


@router.get("/stock/{code}")
async def get_stock_calendar(code: str, days: int = Query(180, ge=1, le=365)):
    """个股未来 N 天催化剂"""
    return stock_calendar(code, days_ahead=days)
