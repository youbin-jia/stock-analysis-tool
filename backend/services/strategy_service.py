"""技术策略引擎：信号判定 + 回测 + 综合评分

设计约束：
- 每个策略的 evaluate(rows, i) 只允许读取 rows[0..i]，禁止读 rows[i+1:]
- 回测进场统一在信号次日收盘，避免"当根发现信号、当根收盘成交"的未来函数
- 综合置信度由各策略的历史胜率加权，权重经贝叶斯收缩，防止小样本高胜率误导

免责：本模块输出的是技术指标规则的机械判定结果，不构成投资建议。
"""

import statistics
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

DISCLAIMER = "本结果由技术指标规则自动生成，仅供研究参考，不构成任何投资建议。"

FAMILY_NAMES = {
    "trend": "趋势跟随",
    "momentum": "动能",
    "volatility": "波动/通道",
    "breakout": "突破",
}

# 按频率缩放的参数
HOLDING_BARS = {"d": 20, "w": 8, "m": 6}
RECENT_WINDOW = {"d": 5, "w": 3, "m": 2}


# ============================ 策略定义 ============================


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    family: str
    min_bars: int
    evaluate: Callable[[List[Dict], int], Optional[Dict]]
    describe_state: Callable[[List[Dict], int], Dict]
    description: str = ""


def _get(rows, i, field_name):
    if i < 0 or i >= len(rows):
        return None
    return rows[i].get(field_name)


def _crossed_up(rows, i, fast_field, slow_field) -> bool:
    """fast 在第 i 根上穿 slow"""
    f0, s0 = _get(rows, i - 1, fast_field), _get(rows, i - 1, slow_field)
    f1, s1 = _get(rows, i, fast_field), _get(rows, i, slow_field)
    if None in (f0, s0, f1, s1):
        return False
    return f0 <= s0 and f1 > s1


def _crossed_down(rows, i, fast_field, slow_field) -> bool:
    f0, s0 = _get(rows, i - 1, fast_field), _get(rows, i - 1, slow_field)
    f1, s1 = _get(rows, i, fast_field), _get(rows, i, slow_field)
    if None in (f0, s0, f1, s1):
        return False
    return f0 >= s0 and f1 < s1


def _crossed_value_up(rows, i, field_name, level) -> bool:
    v0, v1 = _get(rows, i - 1, field_name), _get(rows, i, field_name)
    if v0 is None or v1 is None:
        return False
    return v0 <= level < v1


def _crossed_value_down(rows, i, field_name, level) -> bool:
    v0, v1 = _get(rows, i - 1, field_name), _get(rows, i, field_name)
    if v0 is None or v1 is None:
        return False
    return v0 >= level > v1


# ---------------------------- 趋势跟随 ----------------------------


def _eval_ma_cross(rows, i):
    ma20_now, ma20_prev = _get(rows, i, "ma20"), _get(rows, i - 5, "ma20")
    if _crossed_up(rows, i, "ma5", "ma20"):
        rising = ma20_prev is not None and ma20_now > ma20_prev
        if rising:
            return {"signal": "buy", "strength": 0.8, "reason": "MA5 上穿 MA20，且 MA20 向上"}
        return {"signal": "buy", "strength": 0.4, "reason": "MA5 上穿 MA20，但 MA20 未走平向上"}
    if _crossed_down(rows, i, "ma5", "ma20"):
        return {"signal": "sell", "strength": 0.7, "reason": "MA5 下穿 MA20"}
    return None


def _state_ma_cross(rows, i):
    ma5, ma20 = _get(rows, i, "ma5"), _get(rows, i, "ma20")
    if ma5 is None or ma20 is None:
        return {"status": "neutral", "detail": "均线数据不足"}
    if ma5 > ma20:
        return {"status": "bullish", "detail": f"MA5({ma5}) 高于 MA20({ma20})"}
    return {"status": "bearish", "detail": f"MA5({ma5}) 低于 MA20({ma20})"}


def _aligned(rows, i, bullish=True):
    vals = [_get(rows, i, f"ma{p}") for p in (5, 10, 20, 60)]
    if any(v is None for v in vals):
        return False
    pairs = zip(vals, vals[1:])
    return all(a > b for a, b in pairs) if bullish else all(a < b for a, b in pairs)


def _eval_ma_alignment(rows, i):
    if _aligned(rows, i, True) and not _aligned(rows, i - 1, True):
        return {"signal": "buy", "strength": 0.9, "reason": "均线形成多头排列 MA5>MA10>MA20>MA60"}
    if _aligned(rows, i, False) and not _aligned(rows, i - 1, False):
        return {"signal": "sell", "strength": 0.9, "reason": "均线形成空头排列 MA5<MA10<MA20<MA60"}
    return None


def _state_ma_alignment(rows, i):
    if _aligned(rows, i, True):
        return {"status": "bullish", "detail": "多头排列 MA5>MA10>MA20>MA60"}
    if _aligned(rows, i, False):
        return {"status": "bearish", "detail": "空头排列 MA5<MA10<MA20<MA60"}
    return {"status": "neutral", "detail": "均线交织，方向不明"}


def _eval_none(rows, i):
    return None


def _state_ma200_regime(rows, i):
    close, ma200 = _get(rows, i, "close"), _get(rows, i, "ma200")
    if ma200 is None:
        return {"status": "neutral", "detail": "数据不足 200 根，无法判定长期趋势"}
    ma200_prev = _get(rows, i - 20, "ma200")
    slope = "向上" if ma200_prev is not None and ma200 > ma200_prev else "向下"
    pct = (close - ma200) / ma200 * 100
    if close > ma200:
        return {"status": "bullish", "detail": f"收盘价位于 MA200 上方 {pct:.1f}%，MA200 {slope}"}
    return {"status": "bearish", "detail": f"收盘价位于 MA200 下方 {abs(pct):.1f}%，MA200 {slope}"}


# ---------------------------- 动能 ----------------------------


def _eval_macd_cross(rows, i):
    dif = _get(rows, i, "dif")
    if dif is None:
        return None
    if _crossed_up(rows, i, "dif", "dea"):
        above = dif > 0
        return {
            "signal": "buy",
            "strength": 0.8 if above else 0.5,
            "reason": "DIF 上穿 DEA" + ("，且位于零轴上方" if above else "（零轴下方，属反弹）"),
        }
    if _crossed_down(rows, i, "dif", "dea"):
        below = dif < 0
        return {
            "signal": "sell",
            "strength": 0.8 if below else 0.5,
            "reason": "DIF 下穿 DEA" + ("，且位于零轴下方" if below else ""),
        }
    return None


def _state_macd_cross(rows, i):
    dif, dea = _get(rows, i, "dif"), _get(rows, i, "dea")
    if dif is None or dea is None:
        return {"status": "neutral", "detail": "MACD 数据不足"}
    zone = "零轴上方" if dif > 0 else "零轴下方"
    if dif > dea:
        return {"status": "bullish", "detail": f"DIF 高于 DEA，位于{zone}"}
    return {"status": "bearish", "detail": f"DIF 低于 DEA，位于{zone}"}


def _eval_macd_zero(rows, i):
    if _crossed_value_up(rows, i, "dif", 0):
        return {"signal": "buy", "strength": 0.7, "reason": "DIF 上穿零轴，中期动能转多"}
    if _crossed_value_down(rows, i, "dif", 0):
        return {"signal": "sell", "strength": 0.7, "reason": "DIF 下穿零轴，中期动能转空"}
    return None


def _state_macd_zero(rows, i):
    dif = _get(rows, i, "dif")
    if dif is None:
        return {"status": "neutral", "detail": "MACD 数据不足"}
    if dif > 0:
        return {"status": "bullish", "detail": f"DIF({dif}) 位于零轴上方"}
    return {"status": "bearish", "detail": f"DIF({dif}) 位于零轴下方"}


def detect_macd_divergence(
    rows: List[Dict],
    i: int,
    left: int = 3,
    right: int = 3,
    min_gap: int = 5,
    max_gap: int = 60,
) -> Optional[Dict]:
    """
    MACD 背离检测，只使用 rows[0..i]

    只取【已确认】的摆动点（swing_idx + right <= i），这是避免未来函数的关键。
    另外要求：两点间隔 5~60 根、价格差幅 >1%、DIF 在正确的零轴一侧、信号新鲜。
    """
    if i < 40:
        return None

    def swings(kind: str) -> List[int]:
        out = []
        for idx in range(left, i - right + 1):
            if idx + right > i:
                break
            window = [rows[j].get("close") for j in range(idx - left, idx + right + 1)]
            if any(v is None for v in window):
                continue
            center = window[left]
            others = window[:left] + window[left + 1 :]
            if kind == "low" and all(center < v for v in others):
                out.append(idx)
            elif kind == "high" and all(center > v for v in others):
                out.append(idx)
        return out

    for kind, signal in (("low", "buy"), ("high", "sell")):
        pts = swings(kind)
        if len(pts) < 2:
            continue
        p1, p2 = pts[-2], pts[-1]
        gap = p2 - p1
        if not (min_gap <= gap <= max_gap):
            continue
        if i - p2 > right + 2:  # 信号必须新鲜
            continue

        c1, c2 = rows[p1].get("close"), rows[p2].get("close")
        d1, d2 = rows[p1].get("dif"), rows[p2].get("dif")
        if None in (c1, c2, d1, d2):
            continue

        if signal == "buy":
            ok = c2 < c1 * 0.99 and d2 > d1 and d1 < 0
            text = "价格创新低而 DIF 抬高，底背离"
        else:
            ok = c2 > c1 * 1.01 and d2 < d1 and d1 > 0
            text = "价格创新高而 DIF 走低，顶背离"

        if ok:
            strength = min(1.0, abs(d2 - d1) / (abs(d1) + 1e-9))
            return {
                "signal": signal,
                "strength": max(0.3, min(1.0, strength)),
                "reason": text,
            }
    return None


def _state_macd_divergence(rows, i):
    div = detect_macd_divergence(rows, i)
    if div:
        return {
            "status": "bullish" if div["signal"] == "buy" else "bearish",
            "detail": div["reason"],
        }
    return {"status": "neutral", "detail": "近期未出现有效背离"}


def _eval_rsi_extreme(rows, i):
    # 用"穿回"而非 RSI<30，后者在下跌趋势中每根都会触发
    if _crossed_value_up(rows, i, "rsi14", 30):
        return {"signal": "buy", "strength": 0.7, "reason": "RSI 从超卖区（<30）向上穿回"}
    if _crossed_value_down(rows, i, "rsi14", 70):
        return {"signal": "sell", "strength": 0.7, "reason": "RSI 从超买区（>70）向下穿回"}
    return None


def _state_rsi_extreme(rows, i):
    rsi = _get(rows, i, "rsi14")
    if rsi is None:
        return {"status": "neutral", "detail": "RSI 数据不足"}
    if rsi > 70:
        return {"status": "bearish", "detail": f"RSI({rsi:.1f}) 处于超买区"}
    if rsi < 30:
        return {"status": "bullish", "detail": f"RSI({rsi:.1f}) 处于超卖区"}
    return {"status": "neutral", "detail": f"RSI({rsi:.1f}) 处于中性区间"}


def _eval_rsi_regime(rows, i):
    window = [_get(rows, j, "rsi14") for j in range(max(0, i - 19), i + 1)]
    window = [v for v in window if v is not None]
    if len(window) < 20:
        return None
    if _crossed_value_up(rows, i, "rsi14", 50) and min(window) > 40:
        return {"signal": "buy", "strength": 0.6, "reason": "RSI 上穿 50 且近 20 根未跌破 40，多头区间特征"}
    if _crossed_value_down(rows, i, "rsi14", 50) and max(window) < 60:
        return {"signal": "sell", "strength": 0.6, "reason": "RSI 下穿 50 且近 20 根未站上 60，空头区间特征"}
    return None


def _state_rsi_regime(rows, i):
    rsi = _get(rows, i, "rsi14")
    if rsi is None:
        return {"status": "neutral", "detail": "RSI 数据不足"}
    if rsi > 50:
        return {"status": "bullish", "detail": f"RSI({rsi:.1f}) 位于 50 上方"}
    return {"status": "bearish", "detail": f"RSI({rsi:.1f}) 位于 50 下方"}


# ---------------------------- 波动 / 通道 ----------------------------


def _eval_boll_squeeze(rows, i):
    prev_pct = _get(rows, i - 1, "boll_width_pct")
    close = _get(rows, i, "close")
    upper, lower = _get(rows, i, "boll_upper"), _get(rows, i, "boll_lower")
    if None in (prev_pct, close, upper, lower):
        return None
    if prev_pct >= 20:
        return None
    if close > upper:
        return {"signal": "buy", "strength": 0.9, "reason": "布林带挤压后向上突破上轨"}
    if close < lower:
        return {"signal": "sell", "strength": 0.9, "reason": "布林带挤压后向下跌破下轨"}
    return None


def _state_boll_squeeze(rows, i):
    pct = _get(rows, i, "boll_width_pct")
    if pct is None:
        return {"status": "neutral", "detail": "布林带数据不足"}
    if pct < 20:
        return {"status": "neutral", "detail": f"带宽处于近 120 根的 {pct:.0f}% 分位，处于挤压待变盘"}
    return {"status": "neutral", "detail": f"带宽处于近 120 根的 {pct:.0f}% 分位"}


def _eval_boll_revert(rows, i):
    close = _get(rows, i, "close")
    ma200 = _get(rows, i, "ma200")
    up0, low0 = _get(rows, i - 1, "boll_upper"), _get(rows, i - 1, "boll_lower")
    c0 = _get(rows, i - 1, "close")
    up1, low1 = _get(rows, i, "boll_upper"), _get(rows, i, "boll_lower")
    if None in (close, c0, up0, low0, up1, low1):
        return None

    # 只在长期趋势方向上做均值回归；无 MA200 时（如月线）不加限制
    if c0 < low0 and low1 <= close <= up1:
        if ma200 is None or close > ma200:
            return {"signal": "buy", "strength": 0.6, "reason": "跌破布林下轨后收回带内，超跌修复"}
    if c0 > up0 and low1 <= close <= up1:
        return {"signal": "sell", "strength": 0.6, "reason": "突破布林上轨后收回带内，冲高回落"}
    return None


def _state_boll_revert(rows, i):
    pctb = _get(rows, i, "boll_pctb")
    if pctb is None:
        return {"status": "neutral", "detail": "布林带数据不足"}
    if pctb > 1:
        return {"status": "bearish", "detail": f"价格位于上轨之上（%B={pctb:.2f}）"}
    if pctb < 0:
        return {"status": "bullish", "detail": f"价格位于下轨之下（%B={pctb:.2f}）"}
    return {"status": "neutral", "detail": f"价格位于布林带内（%B={pctb:.2f}）"}


def _eval_kdj_cross(rows, i):
    k, d = _get(rows, i, "k"), _get(rows, i, "d")
    if k is None or d is None:
        return None
    if _crossed_up(rows, i, "k", "d") and k < 30 and d < 30:
        return {"signal": "buy", "strength": 0.7, "reason": "KDJ 低位（<30）金叉"}
    if _crossed_down(rows, i, "k", "d") and k > 70 and d > 70:
        return {"signal": "sell", "strength": 0.7, "reason": "KDJ 高位（>70）死叉"}
    return None


def _state_kdj_cross(rows, i):
    k, d = _get(rows, i, "k"), _get(rows, i, "d")
    if k is None or d is None:
        return {"status": "neutral", "detail": "KDJ 数据不足"}
    zone = "低位" if k < 30 else "高位" if k > 70 else "中位"
    if k > d:
        return {"status": "bullish", "detail": f"K({k:.1f}) 高于 D({d:.1f})，{zone}"}
    return {"status": "bearish", "detail": f"K({k:.1f}) 低于 D({d:.1f})，{zone}"}


# ---------------------------- 突破 ----------------------------


def _make_donchian_eval(period: int):
    def _eval(rows, i):
        close = _get(rows, i, "close")
        upper = _get(rows, i, f"dc{period}_upper")
        lower = _get(rows, i, f"dc{period}_lower")
        prev_close = _get(rows, i - 1, "close")
        prev_upper = _get(rows, i - 1, f"dc{period}_upper")
        prev_lower = _get(rows, i - 1, f"dc{period}_lower")
        if None in (close, upper, lower, prev_close, prev_upper, prev_lower):
            return None
        # 只在首次突破时触发，避免趋势中连续多根重复报信号
        if close > upper and prev_close <= prev_upper:
            return {"signal": "buy", "strength": 0.8, "reason": f"收盘突破前 {period} 日最高价"}
        if close < lower and prev_close >= prev_lower:
            return {"signal": "sell", "strength": 0.8, "reason": f"收盘跌破前 {period} 日最低价"}
        return None

    return _eval


def _make_donchian_state(period: int):
    def _state(rows, i):
        close = _get(rows, i, "close")
        upper = _get(rows, i, f"dc{period}_upper")
        lower = _get(rows, i, f"dc{period}_lower")
        if None in (close, upper, lower):
            return {"status": "neutral", "detail": f"数据不足 {period} 根"}
        if close > upper:
            return {"status": "bullish", "detail": f"价格在前 {period} 日通道上沿之上"}
        if close < lower:
            return {"status": "bearish", "detail": f"价格在前 {period} 日通道下沿之下"}
        return {"status": "neutral", "detail": f"价格在前 {period} 日通道内运行"}

    return _state


# ---------------------------- 注册表 ----------------------------

STRATEGIES: List[Strategy] = [
    Strategy("ma_cross", "均线金叉/死叉", "trend", 25, _eval_ma_cross, _state_ma_cross,
             "MA5 与 MA20 的交叉，配合 MA20 斜率过滤"),
    Strategy("ma_alignment", "均线多空排列", "trend", 65, _eval_ma_alignment, _state_ma_alignment,
             "MA5>MA10>MA20>MA60 首次成立"),
    Strategy("ma200_regime", "MA200 长期趋势", "trend", 200, _eval_none, _state_ma200_regime,
             "只作为市场状态过滤器，不单独产生信号"),
    Strategy("macd_cross", "MACD 金叉/死叉", "momentum", 35, _eval_macd_cross, _state_macd_cross,
             "DIF 与 DEA 交叉，零轴上方权重更高"),
    Strategy("macd_zero_axis", "MACD 零轴穿越", "momentum", 35, _eval_macd_zero, _state_macd_zero,
             "DIF 上穿/下穿零轴"),
    Strategy("macd_divergence", "MACD 背离", "momentum", 45, detect_macd_divergence,
             _state_macd_divergence, "价格与 DIF 的顶/底背离，基于已确认摆动点"),
    Strategy("rsi_extreme", "RSI 超买超卖", "momentum", 20, _eval_rsi_extreme, _state_rsi_extreme,
             "RSI 从 30 下方穿回或从 70 上方穿回"),
    Strategy("rsi_regime", "RSI 区间转换", "momentum", 35, _eval_rsi_regime, _state_rsi_regime,
             "RSI 穿越 50 并结合近 20 根的区间特征"),
    Strategy("boll_squeeze_breakout", "布林挤压突破", "volatility", 140, _eval_boll_squeeze,
             _state_boll_squeeze, "带宽处于历史低分位后向上/向下突破"),
    Strategy("boll_mean_revert", "布林均值回归", "volatility", 25, _eval_boll_revert,
             _state_boll_revert, "破轨后收回带内，顺长期趋势方向"),
    Strategy("kdj_cross", "KDJ 金叉/死叉", "volatility", 15, _eval_kdj_cross, _state_kdj_cross,
             "低位金叉 / 高位死叉"),
    Strategy("donchian_20", "唐奇安20日突破", "breakout", 25, _make_donchian_eval(20),
             _make_donchian_state(20), "海龟系统 System 1"),
    Strategy("donchian_55", "唐奇安55日突破", "breakout", 60, _make_donchian_eval(55),
             _make_donchian_state(55), "海龟系统 System 2"),
]

STRATEGY_MAP = {s.key: s for s in STRATEGIES}


# ============================ 回测 ============================


@dataclass
class BacktestStats:
    signal_count: int = 0
    win_count: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    median_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    max_return: float = 0.0
    min_return: float = 0.0
    holding_bars: int = 0
    sample_quality: str = "insufficient"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_count": self.signal_count,
            "win_count": self.win_count,
            "win_rate": round(self.win_rate, 4),
            "avg_return": round(self.avg_return, 4),
            "median_return": round(self.median_return, 4),
            "avg_win": round(self.avg_win, 4),
            "avg_loss": round(self.avg_loss, 4),
            "expectancy": round(self.expectancy, 4),
            "max_return": round(self.max_return, 4),
            "min_return": round(self.min_return, 4),
            "holding_bars": self.holding_bars,
            "sample_quality": self.sample_quality,
        }


def _quality(n: int) -> str:
    if n >= 20:
        return "good"
    if n >= 8:
        return "weak"
    return "insufficient"


def backtest_strategy(
    rows: List[Dict],
    strategy: Strategy,
    holding_bars: int = 20,
    direction: str = "buy",
) -> BacktestStats:
    """
    单方向回测

    进场：信号次日收盘（防未来函数）
    出场：反向信号次日收盘 / 持满 holding_bars / 数据末尾
          剩余不足 holding_bars 的 60% 时丢弃该样本，避免半截窗口污染统计
    收益：sell 方向取负号，使 win 统一表示"方向判断正确"
    不复利、不计仓位、不扣手续费，只统计方向命中率。
    """
    stats = BacktestStats(holding_bars=holding_bars)
    returns: List[float] = []
    n = len(rows)
    opposite = "sell" if direction == "buy" else "buy"

    i = strategy.min_bars
    while i < n - 1:
        res = strategy.evaluate(rows, i)
        if not res or res.get("signal") != direction:
            i += 1
            continue

        entry_idx = i + 1
        entry = rows[entry_idx].get("close")
        if not entry:
            i += 1
            continue

        exit_idx = min(entry_idx + holding_bars, n - 1)
        for j in range(entry_idx + 1, exit_idx + 1):
            other = strategy.evaluate(rows, j)
            if other and other.get("signal") == opposite:
                exit_idx = min(j + 1, n - 1)
                break

        if exit_idx - entry_idx < holding_bars * 0.6 and exit_idx == n - 1:
            break  # 尾部窗口不完整，丢弃

        exit_price = rows[exit_idx].get("close")
        if not exit_price:
            i += 1
            continue

        ret = (exit_price / entry - 1) * 100
        if direction == "sell":
            ret = -ret
        returns.append(ret)
        i = exit_idx  # 同方向不重叠开仓

    if not returns:
        return stats

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    stats.signal_count = len(returns)
    stats.win_count = len(wins)
    stats.win_rate = len(wins) / len(returns)
    stats.avg_return = sum(returns) / len(returns)
    stats.median_return = statistics.median(returns)
    stats.avg_win = sum(wins) / len(wins) if wins else 0.0
    stats.avg_loss = sum(losses) / len(losses) if losses else 0.0
    stats.expectancy = stats.win_rate * stats.avg_win + (1 - stats.win_rate) * stats.avg_loss
    stats.max_return = max(returns)
    stats.min_return = min(returns)
    stats.sample_quality = _quality(len(returns))
    return stats


def backtest_all(
    rows: List[Dict],
    strategies: List[Strategy],
    holding_bars: int = 20,
) -> Dict[str, Dict[str, BacktestStats]]:
    result = {}
    for s in strategies:
        if s.key == "ma200_regime":
            continue
        result[s.key] = {
            "buy": backtest_strategy(rows, s, holding_bars, "buy"),
            "sell": backtest_strategy(rows, s, holding_bars, "sell"),
        }
    return result


# ============================ 加权与综合评分 ============================


def strategy_weight(stats: BacktestStats) -> float:
    """
    回测胜率映射为权重，范围 [0.2, 1.0]

    先线性放大胜率优势，再按样本量向 0.5 做贝叶斯收缩，
    防止"3 次信号 100% 胜率"这种噪声主导综合评分。
    """
    if stats.signal_count == 0:
        return 0.3
    raw = 0.5 + (stats.win_rate - 0.5) * 2.0
    n = stats.signal_count
    shrunk = (raw * n + 0.5 * 10) / (n + 10)
    return max(0.2, min(1.0, shrunk))


def compute_risk_levels(
    rows: List[Dict],
    atr_mult_stop: float = 2.0,
    atr_mult_target: float = 3.0,
) -> Optional[Dict[str, Any]]:
    """基于最后一根K线的 ATR 给出机械的止损/止盈参考位"""
    if not rows:
        return None
    last = rows[-1]
    close, atr = last.get("close"), last.get("atr14")
    if not close or not atr:
        return None

    stop = close - atr_mult_stop * atr
    target = close + atr_mult_target * atr
    return {
        "close": round(close, 4),
        "atr": round(atr, 4),
        "atr_pct": round(atr / close * 100, 2),
        "stop_loss": round(stop, 4),
        "stop_loss_pct": round((stop / close - 1) * 100, 2),
        "take_profit": round(target, 4),
        "take_profit_pct": round((target / close - 1) * 100, 2),
        "risk_reward": round(atr_mult_target / atr_mult_stop, 2),
        "basis": f"ATR(14) × {atr_mult_stop:g} 止损 / × {atr_mult_target:g} 止盈",
    }


def compute_composite(
    rows: List[Dict],
    strategies: List[Strategy],
    backtests: Dict[str, Dict[str, BacktestStats]],
    frequency: str = "d",
) -> Dict[str, Any]:
    """
    综合当前信号

    对每个策略在最近 recent_window 根内寻找最后一次触发，
    贡献 = 回测权重 × 信号强度 × 时间衰减；买卖分数独立累加。
    """
    i = len(rows) - 1
    recent = RECENT_WINDOW.get(frequency, 5)

    buy_score = sell_score = max_possible = 0.0
    reasons: List[Dict[str, Any]] = []

    regime = _state_ma200_regime(rows, i)

    for s in strategies:
        if s.key == "ma200_regime" or len(rows) <= s.min_bars:
            continue

        fired = None
        for j in range(i, max(s.min_bars - 1, i - recent), -1):
            res = s.evaluate(rows, j)
            if res:
                fired = (j, res)
                break

        direction = fired[1]["signal"] if fired else "buy"
        stats = backtests.get(s.key, {}).get(direction, BacktestStats())
        weight = strategy_weight(stats)
        max_possible += weight

        if not fired:
            continue

        j, res = fired
        age = i - j
        decay = 1 - age / (recent + 1)
        contrib = weight * res.get("strength", 0.5) * decay

        if res["signal"] == "buy":
            buy_score += contrib
        else:
            sell_score += contrib

        reasons.append({
            "strategy_key": s.key,
            "strategy_name": s.name,
            "family": s.family,
            "family_name": FAMILY_NAMES.get(s.family, s.family),
            "signal": res["signal"],
            "date": rows[j]["date"],
            "bars_ago": age,
            "strength": round(res.get("strength", 0.5), 3),
            "weight": round(weight, 3),
            "backtest_win_rate": round(stats.win_rate, 4),
            "backtest_count": stats.signal_count,
            "detail": res.get("reason", ""),
        })

    # 市场状态过滤：长期趋势向下时压低买入、放大卖出
    if regime["status"] == "bearish":
        buy_score *= 0.7
        sell_score *= 1.15
    elif regime["status"] == "bullish":
        sell_score *= 0.85

    net = (buy_score - sell_score) / max(max_possible, 1e-9)
    confidence = min(100, round(abs(net) * 100 * 1.6))

    if net >= 0.15:
        verdict = "买入"
    elif net <= -0.15:
        verdict = "卖出"
    else:
        verdict = "观望"

    reasons.sort(key=lambda r: (r["bars_ago"], -r["weight"]))

    return {
        "verdict": verdict,
        "confidence": int(confidence),
        "net_score": round(net, 4),
        "buy_score": round(buy_score, 4),
        "sell_score": round(sell_score, 4),
        "regime": regime,
        "reasons": reasons,
    }


def collect_markers(
    rows: List[Dict],
    strategies: List[Strategy],
    start: str,
) -> List[Dict[str, Any]]:
    """
    收集历史信号点，同日同方向的多个策略合并为一个标记

    不合并的话 ECharts 会在同一根K线上叠多个箭头，完全无法阅读。
    """
    bucket: Dict[tuple, Dict[str, Any]] = {}

    for s in strategies:
        if s.key == "ma200_regime":
            continue
        for i in range(s.min_bars, len(rows)):
            if rows[i]["date"] < start:
                continue
            res = s.evaluate(rows, i)
            if not res:
                continue
            key = (rows[i]["date"], res["signal"])
            entry = bucket.setdefault(key, {
                "date": rows[i]["date"],
                "type": res["signal"],
                "price": rows[i]["close"],
                "members": [],
                "names": [],
                "strength": 0.0,
            })
            entry["members"].append(s.key)
            entry["names"].append(s.name)
            entry["strength"] = max(entry["strength"], res.get("strength", 0.5))

    markers = []
    for entry in bucket.values():
        count = len(entry["members"])
        markers.append({
            "date": entry["date"],
            "type": entry["type"],
            "price": entry["price"],
            "strategy_key": entry["members"][0] if count == 1 else "multi",
            "strategy_name": entry["names"][0] if count == 1 else f"{count} 个策略共振",
            "label": entry["names"][0] if count == 1 else f"共振×{count}",
            "members": entry["members"],
            "member_names": entry["names"],
            "strength": round(entry["strength"], 3),
        })

    markers.sort(key=lambda m: m["date"])
    return markers
