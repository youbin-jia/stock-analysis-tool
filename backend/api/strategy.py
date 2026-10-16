"""技术策略信号接口

返回内容均为技术指标规则的机械判定结果，不构成投资建议。
"""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.cache_service import CacheService
from services.history_loader import (
    STRATEGY_WARMUP_DAYS, load_history_with_warmup, resolve_period_range
)
from services.indicator_service import compute_all_indicators, compute_macd
from services.strategy_service import (
    DISCLAIMER,
    FAMILY_NAMES,
    HOLDING_BARS,
    STRATEGIES,
    backtest_all,
    collect_markers,
    compute_composite,
    compute_risk_levels,
    strategy_weight,
)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

# 少于这个K线数就不做技术分析，直接返回观望
MIN_BARS_FOR_ANALYSIS = 60


@router.get("/definitions")
async def list_strategy_definitions():
    """返回全部策略定义，供前端做图例与说明"""
    return {
        "families": FAMILY_NAMES,
        "strategies": [
            {
                "key": s.key,
                "name": s.name,
                "family": s.family,
                "family_name": FAMILY_NAMES.get(s.family, s.family),
                "min_bars": s.min_bars,
                "description": s.description,
            }
            for s in STRATEGIES
        ],
        "disclaimer": DISCLAIMER,
    }


@router.get("/signals/{code}")
def get_strategy_signals(
    code: str,
    period: Optional[str] = Query("1y", description="时间周期: 1m, 3m, 6m, 1y, all"),
    frequency: Optional[str] = Query("d", description="K线频率: d=日线, w=周线, m=月线"),
    holding: Optional[int] = Query(None, description="回测持有周期(根)，默认按频率取值"),
):
    """
    技术策略买卖信号

    在含预热段的完整序列上计算指标与回测，综合评分取最后一根K线，
    历史标记裁剪回请求区间后返回。
    """
    if frequency not in ("d", "w", "m"):
        raise HTTPException(status_code=400, detail="frequency 仅支持 d / w / m")

    holding_bars = holding or HOLDING_BARS[frequency]
    if holding_bars < 2 or holding_bars > 250:
        raise HTTPException(status_code=400, detail="holding 需在 2~250 之间")

    cached = CacheService.get_cached_strategy(code, period, frequency, holding_bars)
    if cached:
        return json.loads(cached)

    start, end = resolve_period_range(period)
    rows = load_history_with_warmup(
        code, start, end, frequency, STRATEGY_WARMUP_DAYS[frequency]
    )

    base = {
        "code": code,
        "period": period,
        "frequency": frequency,
        "start": start,
        "end": end,
        "holding_bars": holding_bars,
        "disclaimer": DISCLAIMER,
    }

    if len(rows) < MIN_BARS_FOR_ANALYSIS:
        return {
            **base,
            "bars": len(rows),
            "last_date": rows[-1]["date"] if rows else None,
            "last_close": rows[-1]["close"] if rows else None,
            "composite": {
                "verdict": "观望",
                "confidence": 0,
                "net_score": 0.0,
                "buy_score": 0.0,
                "sell_score": 0.0,
                "regime": {"status": "neutral", "detail": "数据不足，无法判定"},
                "reasons": [],
            },
            "risk_levels": None,
            "strategies": [],
            "markers": [],
            "warnings": [f"历史数据仅 {len(rows)} 根，不足 {MIN_BARS_FOR_ANALYSIS} 根，无法进行技术分析"],
            "methodology": _methodology(holding_bars),
        }

    compute_macd(rows)
    compute_all_indicators(rows)

    # 数据长度不够的策略本次直接剔除，而不是让它产出失真信号
    available = [s for s in STRATEGIES if len(rows) > s.min_bars]
    dropped = [s.name for s in STRATEGIES if len(rows) <= s.min_bars]

    backtests = backtest_all(rows, available, holding_bars)
    composite = compute_composite(rows, available, backtests, frequency)
    markers = collect_markers(rows, available, start)
    risk = compute_risk_levels(rows)

    last_idx = len(rows) - 1
    strategy_details = []
    for s in available:
        stats = backtests.get(s.key)
        state = s.describe_state(rows, last_idx)

        last_signal = None
        for j in range(last_idx, s.min_bars - 1, -1):
            res = s.evaluate(rows, j)
            if res:
                last_signal = {
                    "signal": res["signal"],
                    "date": rows[j]["date"],
                    "bars_ago": last_idx - j,
                    "detail": res.get("reason", ""),
                }
                break

        entry = {
            "key": s.key,
            "name": s.name,
            "family": s.family,
            "family_name": FAMILY_NAMES.get(s.family, s.family),
            "description": s.description,
            "status": state["status"],
            "detail": state["detail"],
            "fired": bool(last_signal and last_signal["bars_ago"] == 0),
            "last_signal": last_signal,
        }
        if stats:
            direction = last_signal["signal"] if last_signal else "buy"
            entry["weight"] = round(strategy_weight(stats[direction]), 3)
            entry["backtest"] = {
                "buy": stats["buy"].to_dict(),
                "sell": stats["sell"].to_dict(),
            }
        else:
            entry["weight"] = None
            entry["backtest"] = None
        strategy_details.append(entry)

    warnings = []
    if dropped:
        warnings.append(f"数据长度不足，已跳过以下策略：{'、'.join(dropped)}")

    result = {
        **base,
        "bars": len(rows),
        "last_date": rows[-1]["date"],
        "last_close": rows[-1]["close"],
        "composite": composite,
        "risk_levels": risk,
        "strategies": strategy_details,
        "markers": markers,
        "warnings": warnings,
        "methodology": _methodology(holding_bars),
    }

    CacheService.set_cached_strategy(
        code, period, frequency, holding_bars, json.dumps(result, ensure_ascii=False)
    )
    return result


def _methodology(holding_bars: int) -> dict:
    return {
        "in_sample_weighting": True,
        "entry_rule": "信号次日收盘价进场",
        "exit_rule": f"反向信号次日收盘，或持有满 {holding_bars} 根",
        "cost_model": "未计手续费与滑点",
        "note": (
            "各策略权重由全样本回测胜率经贝叶斯收缩得出，属样本内统计，"
            "存在过拟合倾向；历史胜率不代表未来表现。"
        ),
    }
