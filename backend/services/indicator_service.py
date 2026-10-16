"""技术指标计算（纯函数，不依赖外部数据源）

约定：
- rows 按日期升序，每项至少含 open/high/low/close
- 所有函数原地写入字段并返回 rows
- 指标尚未成熟的 K 线写 None，由策略层负责跳过（不回填种子值）
"""

import math
from typing import Any, Dict, List, Optional


def compute_macd(
    rows: List[Dict[str, Any]],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> List[Dict[str, Any]]:
    """
    为K线数据附加 MACD 指标（原地写入 dif / dea / macd 三个字段）

    采用与主流行情软件一致的算法：
      EMA(fast) - EMA(slow) = DIF
      DIF 的 EMA(signal) = DEA
      MACD = (DIF - DEA) * 2

    rows 需按日期升序排列，每项包含 close 字段。
    """
    if not rows:
        return rows

    fast_alpha = 2 / (fast + 1)
    slow_alpha = 2 / (slow + 1)
    signal_alpha = 2 / (signal + 1)

    ema_fast = ema_slow = dea = None

    for row in rows:
        close = row.get("close") or 0.0

        if ema_fast is None:
            ema_fast, ema_slow, dea = close, close, 0.0
        else:
            ema_fast += fast_alpha * (close - ema_fast)
            ema_slow += slow_alpha * (close - ema_slow)

        dif = ema_fast - ema_slow
        dea += signal_alpha * (dif - dea)

        row["dif"] = round(dif, 4)
        row["dea"] = round(dea, 4)
        row["macd"] = round((dif - dea) * 2, 4)

    return rows


def compute_ma(
    rows: List[Dict[str, Any]],
    periods: tuple = (5, 10, 20, 60, 200),
) -> List[Dict[str, Any]]:
    """简单移动平均，写入 ma5 / ma10 / ma20 / ma60 / ma200，不足周期写 None"""
    closes = [row.get("close") or 0.0 for row in rows]

    for period in periods:
        field = f"ma{period}"
        window_sum = 0.0
        for i, close in enumerate(closes):
            window_sum += close
            if i >= period:
                window_sum -= closes[i - period]
            rows[i][field] = round(window_sum / period, 4) if i >= period - 1 else None

    return rows


def compute_ema(
    rows: List[Dict[str, Any]],
    periods: tuple = (12, 26),
) -> List[Dict[str, Any]]:
    """指数移动平均，alpha = 2/(n+1)，种子用前 n 根的 SMA"""
    closes = [row.get("close") or 0.0 for row in rows]

    for period in periods:
        field = f"ema{period}"
        alpha = 2 / (period + 1)
        ema: Optional[float] = None
        for i, close in enumerate(closes):
            if i < period - 1:
                rows[i][field] = None
                continue
            if ema is None:
                ema = sum(closes[: period]) / period
            else:
                ema += alpha * (close - ema)
            rows[i][field] = round(ema, 4)

    return rows


def compute_rsi(rows: List[Dict[str, Any]], period: int = 14) -> List[Dict[str, Any]]:
    """
    Wilder RSI，写入 rsi{period}

    首值用前 period 根涨跌幅均值做种子，之后 avg = (avg*(p-1) + cur) / p
    avg_loss 为 0 时 RSI 记 100
    """
    field = f"rsi{period}"
    closes = [row.get("close") or 0.0 for row in rows]

    if len(closes) <= period:
        for row in rows:
            row[field] = None
        return rows

    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(len(rows)):
        if i < period:
            rows[i][field] = None
            continue
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi = 100.0
        elif avg_gain == 0:
            rsi = 0.0
        else:
            rsi = 100 - 100 / (1 + avg_gain / avg_loss)
        rows[i][field] = round(rsi, 4)

    return rows


def compute_kdj(
    rows: List[Dict[str, Any]],
    n: int = 9,
    k_period: int = 3,
    d_period: int = 3,
) -> List[Dict[str, Any]]:
    """
    KDJ 随机指标，写入 k / d / j

    RSV = (close - LLV(low, n)) / (HHV(high, n) - LLV(low, n)) * 100
    K = K_prev * (k-1)/k + RSV / k，K/D 初值 50，J = 3K - 2D
    HHV == LLV 时沿用上一根 RSV，避免除零
    """
    k_val, d_val = 50.0, 50.0
    rsv = 50.0

    for i, row in enumerate(rows):
        if i < n - 1:
            row["k"] = row["d"] = row["j"] = None
            continue

        window = rows[i - n + 1 : i + 1]
        highest = max(r.get("high") or 0.0 for r in window)
        lowest = min(r.get("low") or 0.0 for r in window)
        close = row.get("close") or 0.0

        if highest != lowest:
            rsv = (close - lowest) / (highest - lowest) * 100

        k_val = k_val * (k_period - 1) / k_period + rsv / k_period
        d_val = d_val * (d_period - 1) / d_period + k_val / d_period

        row["k"] = round(k_val, 4)
        row["d"] = round(d_val, 4)
        row["j"] = round(3 * k_val - 2 * d_val, 4)

    return rows


def compute_boll(
    rows: List[Dict[str, Any]],
    period: int = 20,
    num_std: float = 2.0,
) -> List[Dict[str, Any]]:
    """
    布林带，写入 boll_mid / boll_upper / boll_lower / boll_width / boll_pctb

    标准差用总体标准差（ddof=0），与行情软件一致
    boll_width = (upper - lower) / mid * 100  带宽百分比，用于挤压判定
    boll_pctb  = (close - lower) / (upper - lower)  价格在带内的相对位置
    """
    closes = [row.get("close") or 0.0 for row in rows]

    for i, row in enumerate(rows):
        if i < period - 1:
            row["boll_mid"] = row["boll_upper"] = row["boll_lower"] = None
            row["boll_width"] = row["boll_pctb"] = None
            continue

        window = closes[i - period + 1 : i + 1]
        mid = sum(window) / period
        variance = sum((c - mid) ** 2 for c in window) / period
        std = math.sqrt(variance)

        upper = mid + num_std * std
        lower = mid - num_std * std

        row["boll_mid"] = round(mid, 4)
        row["boll_upper"] = round(upper, 4)
        row["boll_lower"] = round(lower, 4)
        row["boll_width"] = round((upper - lower) / mid * 100, 4) if mid else None
        row["boll_pctb"] = (
            round((closes[i] - lower) / (upper - lower), 4) if upper != lower else None
        )

    return rows


def compute_boll_squeeze_rank(
    rows: List[Dict[str, Any]],
    lookback: int = 120,
) -> List[Dict[str, Any]]:
    """
    写入 boll_width_pct：当前带宽在过去 lookback 根中的百分位（0~100），< 20 视为挤压

    用分位数而非绝对带宽阈值，因为 ETF 的波动率远低于个股，
    绝对阈值无法跨品种复用。
    """
    for i, row in enumerate(rows):
        width = row.get("boll_width")
        if width is None:
            row["boll_width_pct"] = None
            continue

        window = [
            r.get("boll_width")
            for r in rows[max(0, i - lookback + 1) : i + 1]
            if r.get("boll_width") is not None
        ]
        if len(window) < 20:
            row["boll_width_pct"] = None
            continue

        below = sum(1 for w in window if w < width)
        row["boll_width_pct"] = round(below / len(window) * 100, 4)

    return rows


def compute_atr(rows: List[Dict[str, Any]], period: int = 14) -> List[Dict[str, Any]]:
    """
    Wilder ATR，写入 tr 与 atr{period}

    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    首值取前 period 根 TR 均值，之后 atr = (atr*(p-1) + tr) / p
    """
    field = f"atr{period}"

    for i, row in enumerate(rows):
        high = row.get("high") or 0.0
        low = row.get("low") or 0.0
        if i == 0:
            row["tr"] = round(high - low, 4)
        else:
            prev_close = rows[i - 1].get("close") or 0.0
            row["tr"] = round(
                max(high - low, abs(high - prev_close), abs(low - prev_close)), 4
            )

    atr: Optional[float] = None
    for i, row in enumerate(rows):
        if i < period - 1:
            row[field] = None
            continue
        if atr is None:
            atr = sum(r["tr"] for r in rows[:period]) / period
        else:
            atr = (atr * (period - 1) + row["tr"]) / period
        row[field] = round(atr, 4)

    return rows


def compute_donchian(
    rows: List[Dict[str, Any]],
    periods: tuple = (20, 55),
) -> List[Dict[str, Any]]:
    """
    唐奇安通道，写入 dc{p}_upper / dc{p}_lower / dc{p}_mid

    关键：通道用【不含当根】的前 p 根 high/low（rows[i-p:i]），
    否则 close > upper 永远不成立（当根自己就是区间最高价）。
    """
    highs = [row.get("high") or 0.0 for row in rows]
    lows = [row.get("low") or 0.0 for row in rows]

    for period in periods:
        up_field = f"dc{period}_upper"
        low_field = f"dc{period}_lower"
        mid_field = f"dc{period}_mid"

        for i, row in enumerate(rows):
            if i < period:
                row[up_field] = row[low_field] = row[mid_field] = None
                continue
            upper = max(highs[i - period : i])
            lower = min(lows[i - period : i])
            row[up_field] = round(upper, 4)
            row[low_field] = round(lower, 4)
            row[mid_field] = round((upper + lower) / 2, 4)

    return rows


def find_swing_points(
    rows: List[Dict[str, Any]],
    key: str = "close",
    left: int = 3,
    right: int = 3,
) -> Dict[str, List[int]]:
    """
    分形摆动高低点检测，返回 {"highs": [idx...], "lows": [idx...]}

    只有当 rows[i][key] 严格大于（小于）左右各 left / right 根时才计入。

    注意：一个摆动点要到 i + right 根之后才被【确认】，
    调用方必须用 confirm_index = i + right 作为该点可用的最早时间，
    否则会引入未来函数。
    """
    highs: List[int] = []
    lows: List[int] = []

    for i in range(left, len(rows) - right):
        value = rows[i].get(key)
        if value is None:
            continue

        window = rows[i - left : i + right + 1]
        values = [r.get(key) for r in window]
        if any(v is None for v in values):
            continue

        others = values[:left] + values[left + 1 :]
        if all(value > v for v in others):
            highs.append(i)
        elif all(value < v for v in others):
            lows.append(i)

    return {"highs": highs, "lows": lows}


def compute_all_indicators(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """一次性附加全部技术指标（MACD 由 compute_macd 单独负责）"""
    if not rows:
        return rows

    compute_ma(rows)
    compute_ema(rows)
    compute_rsi(rows)
    compute_kdj(rows)
    compute_boll(rows)
    compute_boll_squeeze_rank(rows)
    compute_atr(rows)
    compute_donchian(rows)
    return rows
