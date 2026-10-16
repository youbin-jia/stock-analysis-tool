"""历史K线加载：周期解析 + 预热窗口 + 本地/远程数据源编排

指标（MACD、MA200、唐奇安通道等）都是递归或长窗口的，必须在请求区间之前
多取一段数据预热，算完再裁剪回请求区间，否则区间起点的指标会失真。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from services.data_service import DataService
from services.stock_service import StockService

# K线接口的预热窗口（自然日）。够 MACD 收敛用
WARMUP_DAYS = {"d": 200, "w": 900, "m": 3600}

# 策略接口的预热窗口（自然日）。需覆盖 MA200 + 唐奇安55 + 120根挤压分位，
# 日线约需 380 个交易日，按 1.45 倍折算成自然日
STRATEGY_WARMUP_DAYS = {"d": 560, "w": 2200, "m": 7300}

# 本地数据被判定为"滞后/缺失"的容忍间隔（自然日）
MAX_GAP_DAYS = {"d": 5, "w": 12, "m": 45}


def resolve_period_range(period: str) -> Tuple[str, str]:
    """把 1m / 3m / 6m / 1y / all 映射为 (start, end) 日期字符串"""
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

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def _gap_days(later: str, earlier: str) -> int:
    return (
        datetime.strptime(later, "%Y-%m-%d") - datetime.strptime(earlier, "%Y-%m-%d")
    ).days


def load_history_with_warmup(
    code: str,
    start: str,
    end: str,
    frequency: str,
    warmup_days: int,
) -> List[Dict[str, Any]]:
    """
    加载 [start - warmup_days, end] 区间的K线，返回**含预热段**的完整序列（不裁剪）

    优先读 SQLite；本地数据不足、覆盖不全或已滞后时远程整段覆盖并回写。
    整段覆盖而非只补尾部，保证前复权价格来自同一数据源、不会出现拼接跳变。
    """
    fetch_start = (
        datetime.strptime(start, "%Y-%m-%d") - timedelta(days=warmup_days)
    ).strftime("%Y-%m-%d")

    data = DataService.load_from_database(code, fetch_start, end, frequency)

    max_gap = MAX_GAP_DAYS[frequency]
    incomplete = bool(data) and (
        _gap_days(end, data[-1]["date"]) > max_gap  # 尾部滞后
        or _gap_days(data[0]["date"], fetch_start) > max_gap  # 头部缺失
    )

    if len(data) < 5 or incomplete:
        api_data = StockService.get_historical_data(code, fetch_start, end, frequency)
        if api_data:
            DataService.save_to_database(code, api_data, frequency)
            data = api_data

    return data or []
