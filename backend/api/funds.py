from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
import json
import threading
from services.fund_service import FundService
from services.data_service import DataService
from services.cache_service import CacheService
from models.database import get_db
from models.schemas import (
    FundInfo, FundListItem, FundHistoryData, FundComparisonResponse
)

router = APIRouter(prefix="/api/funds", tags=["funds"])


@router.get("/list", response_model=List[FundListItem])
async def get_fund_list(keyword: Optional[str] = Query(None, description="搜索关键词")):
    """获取基金列表（带缓存）"""
    # 尝试从缓存获取全量列表
    if not keyword:
        cached = CacheService.get_cached_fund_list()
        if cached:
            return cached

    data = FundService.get_fund_list(keyword)

    # 缓存全量列表
    if not keyword and data:
        CacheService.set_cached_fund_list(data)

    return data


@router.get("/search", response_model=List[FundListItem])
async def search_funds(keyword: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索基金"""
    return FundService.get_fund_list(keyword)


@router.get("/info/{code}", response_model=FundInfo)
async def get_fund_info(code: str):
    """获取基金基本信息"""
    db = next(get_db())
    try:
        from models.database import Fund
        fund = db.query(Fund).filter(Fund.code == code).first()
        if fund:
            return FundInfo(
                code=fund.code,
                name=fund.name,
                fund_type=fund.fund_type
            )
    finally:
        db.close()

    api_info = FundService.get_fund_info(code)
    if not api_info:
        raise HTTPException(status_code=404, detail="Fund not found")

    DataService.save_fund_info(code, api_info)

    return FundInfo(
        code=api_info['code'],
        name=api_info['name'],
        fund_type=api_info.get('type')
    )


@router.get("/history/{code}")
async def get_fund_history(
    code: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = Query("all", description="时间周期: 1m, 3m, 6m, 1y, all"),
):
    """
    获取基金历史净值数据
    优先从本地数据库读取，缺失部分从 eastmoney 增量补充
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
    cached_data = CacheService.get_cached_fund_history(code, start, end)
    if cached_data:
        import json
        return json.loads(cached_data)

    # 从数据库加载
    db_data = DataService.load_fund_from_database(code, start, end)

    # 对于基金，eastmoney 接口一次请求返回全部历史数据，调用成本与日期范围无关
    # 因此当请求全部数据、或数据库数据不足时，直接从 API 获取全量并入库
    if period == "all" or not db_data or len(db_data) < 5:
        api_data = FundService.get_fund_history(code, None, None)
        if api_data:
            DataService.save_fund_to_database(code, api_data)
            if period == "all":
                db_data = api_data
            else:
                db_data = DataService.load_fund_from_database(code, start, end)
    else:
        # 增量更新：只补充最新日期到 end 之间的数据
        latest_date = DataService.get_fund_latest_date_in_db(code)
        if latest_date:
            latest_str = latest_date.strftime("%Y-%m-%d")
            if latest_str < end:
                next_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                api_data = FundService.get_fund_history(code, next_date, end)
                if api_data:
                    DataService.save_fund_to_database(code, api_data)
                    db_data = DataService.load_fund_from_database(code, start, end)

    # 缓存数据
    if db_data:
        import json
        CacheService.set_cached_fund_history(code, start, end, json.dumps(db_data))

    return db_data or []


@router.get("/comparison", response_model=FundComparisonResponse)
async def compare_funds(
    codes: str = Query(..., description="基金代码，逗号分隔，如: 000001,000002"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = Query("all", description="时间周期: 1m, 3m, 6m, 1y, all"),
    normalize: bool = Query(True, description="是否归一化（计算收益率）"),
):
    """
    多基金对比
    """
    code_list = [c.strip() for c in codes.split(',')]
    if not code_list:
        raise HTTPException(status_code=400, detail="At least one fund code is required")

    fetch_full = False
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
            fetch_full = True
            start_date = end_date - timedelta(days=3650)

        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")

    comparison_data = DataService.compare_funds(code_list, start, end, normalize, fetch_full=fetch_full)

    funds_data = []
    for fund in comparison_data['funds']:
        funds_data.append({
            'code': fund['code'],
            'name': fund['name'],
            'data': fund['data']
        })

    return FundComparisonResponse(
        funds=funds_data,
        start_date=start,
        end_date=end
    )


@router.get("/low-position")
async def get_low_position_funds(
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    refresh: bool = Query(False, description="是否强制刷新数据"),
    max_scan: Optional[int] = Query(None, ge=100, description="扫描基金数量，None 表示全市场"),
):
    """
    获取处于历史低位的基金列表
    按历史最大回撤排序，返回回撤最大的前 N 只基金
    默认扫描全市场（排除货币型），使用后台线程异步执行
    """
    # 尝试读取缓存
    if not refresh:
        cached = CacheService.get_cached_low_position_funds()
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    # 检查是否正在扫描中
    scanning = CacheService.get_low_position_scan_status()
    if scanning:
        return {
            "scanning": True,
            "message": "正在扫描全市场基金数据，请稍后再试",
            "data": [],
        }

    # 设置扫描状态并启动后台线程
    CacheService.set_low_position_scan_status("scanning")

    def _do_scan():
        try:
            scan_result = FundService.scan_low_position_funds(
                limit=limit,
                max_scan=max_scan,
                min_history_days=730,
            )
            response = {
                "scanning": False,
                "count": len(scan_result["results"]),
                "scanned": scan_result["total_scanned"],
                "updated_at": datetime.now().isoformat(),
                "data": scan_result["results"],
            }
            CacheService.set_cached_low_position_funds(json.dumps(response))
        except Exception as e:
            print(f"后台扫描低位基金错误: {e}")
        finally:
            CacheService.clear_low_position_scan_status()

    thread = threading.Thread(target=_do_scan, daemon=True)
    thread.start()

    return {
        "scanning": True,
        "message": "已启动全市场基金扫描，请稍后再试",
        "data": [],
    }


@router.get("/holdings/{code}")
async def get_fund_holdings_endpoint(code: str):
    """
    获取基金持仓数据（前十大重仓股）
    """
    holdings = FundService.get_fund_holdings(code)
    if holdings is None:
        raise HTTPException(status_code=404, detail="Holdings data not found")
    return {"code": code, "holdings": holdings}


@router.get("/estimate/{code}")
async def get_fund_estimate(code: str):
    """
    获取基金实时估值
    """
    estimate = FundService.get_fund_realtime_estimate(code)
    if estimate is None:
        raise HTTPException(status_code=404, detail="Estimate data not found")
    return estimate
