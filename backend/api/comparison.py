from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from services.data_service import DataService
from models.schemas import ComparisonResponse

router = APIRouter(prefix="/api/comparison", tags=["comparison"])


@router.get("", response_model=ComparisonResponse)
async def compare_stocks(
    codes: str = Query(..., description="股票代码，逗号分隔，如: 600519,000858"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = Query("1y", description="时间周期: 1m, 3m, 6m, 1y, all"),
    normalize: bool = Query(True, description="是否归一化（计算收益率）"),
    frequency: Optional[str] = Query("d", description="K线频率: d=日线, w=周线, m=月线"),
):
    """
    多股票对比
    """
    code_list = [c.strip() for c in codes.split(',')]
    if not code_list:
        raise HTTPException(status_code=400, detail="At least one stock code is required")

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

    comparison_data = DataService.compare_stocks(code_list, start, end, normalize, frequency)

    stocks_data = []
    for stock in comparison_data['stocks']:
        stocks_data.append({
            'code': stock['code'],
            'name': stock['name'],
            'data': stock['data']
        })

    return ComparisonResponse(
        stocks=stocks_data,
        start_date=start,
        end_date=end
    )
