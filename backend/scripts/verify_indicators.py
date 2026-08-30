"""技术指标验证脚本

覆盖四类检查：
1. 合成序列的确定性断言（单调涨/跌、V型、恒定价格）
2. 与 pandas 参照实现的数值交叉验证
3. 未来函数守卫：截断到第 i 根重算，结果必须与全量数据在第 i 根上一致
4. 唐奇安通道 off-by-one 断言

用法：cd backend && ./venv/bin/python scripts/verify_indicators.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy

import pandas as pd

from services.indicator_service import (
    compute_all_indicators,
    compute_atr,
    compute_boll,
    compute_donchian,
    compute_kdj,
    compute_ma,
    compute_macd,
    compute_rsi,
    find_swing_points,
)

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def make_rows(closes, spread=0.0):
    """
    由收盘价序列构造 OHLC

    spread=0 时 high=low=close，让 KDJ/唐奇安的期望值可以精确推导；
    人为放大 high/low 会改变 RSV 与通道边界，使断言失去意义。
    """
    return [
        {
            "date": f"2020-01-{i + 1:02d}",
            "open": c,
            "close": c,
            "high": c * (1 + spread),
            "low": c * (1 - spread),
            "volume": 1000,
        }
        for i, c in enumerate(closes)
    ]


def test_monotonic_up():
    print("\n[1] 单调上涨序列")
    rows = make_rows([100 + i for i in range(300)])
    compute_macd(rows)
    compute_all_indicators(rows)
    last = rows[-1]

    check("RSI ≈ 100", abs(last["rsi14"] - 100) < 0.1, f"rsi={last['rsi14']}")
    check(
        "均线完全多头排列",
        last["ma5"] > last["ma10"] > last["ma20"] > last["ma60"] > last["ma200"],
    )
    check("K > 99", last["k"] > 99, f"k={last['k']}")
    check("D > 99", last["d"] > 99, f"d={last['d']}")
    check("DIF > 0", last["dif"] > 0, f"dif={last['dif']}")
    check("收盘价持续突破唐奇安上轨", last["close"] > last["dc20_upper"])


def test_monotonic_down():
    print("\n[2] 单调下跌序列")
    rows = make_rows([400 - i for i in range(300)])
    compute_macd(rows)
    compute_all_indicators(rows)
    last = rows[-1]

    check("RSI ≈ 0", abs(last["rsi14"]) < 0.1, f"rsi={last['rsi14']}")
    check(
        "均线完全空头排列",
        last["ma5"] < last["ma10"] < last["ma20"] < last["ma60"] < last["ma200"],
    )
    check("K < 1", last["k"] < 1, f"k={last['k']}")
    check("DIF < 0", last["dif"] < 0, f"dif={last['dif']}")
    check("收盘价持续跌破唐奇安下轨", last["close"] < last["dc20_lower"])


def test_flat():
    print("\n[3] 恒定价格序列（除零与 NaN 防护）")
    rows = make_rows([50.0] * 300)
    compute_macd(rows)
    compute_all_indicators(rows)
    last = rows[-1]

    numeric = [v for v in last.values() if isinstance(v, float)]
    check("无 NaN", all(v == v for v in numeric))
    check("MACD 恒为 0", abs(last["macd"]) < 1e-9, f"macd={last['macd']}")
    check("布林带宽为 0", abs(last["boll_width"]) < 1e-9)
    check("MA5 == MA200", abs(last["ma5"] - last["ma200"]) < 1e-9)
    check("唐奇安上下轨相等", abs(last["dc20_upper"] - last["dc20_lower"]) < 1e-9)


def test_v_shape():
    print("\n[4] V 型序列（先跌后涨）")
    closes = [200 - i for i in range(100)] + [100 + i for i in range(100)]
    rows = make_rows(closes)
    compute_macd(rows)
    compute_all_indicators(rows)

    ma_diff = [
        (i, r["ma5"] - r["ma20"])
        for i, r in enumerate(rows)
        if r.get("ma5") is not None and r.get("ma20") is not None
    ]
    crosses = [
        ("死叉" if prev > 0 >= cur else "金叉")
        for (_, prev), (_, cur) in zip(ma_diff, ma_diff[1:])
        if (prev > 0) != (cur > 0)
    ]
    # 序列一开始就处于空头状态（MA5 < MA20），没有"转为空头"的穿越动作，
    # 所以全程只应出现一次金叉
    check("恰好一次金叉且无死叉", crosses == ["金叉"], f"crosses={crosses}")

    swings = find_swing_points(rows)
    check("V 型底部被识别为摆动低点", any(95 <= i <= 105 for i in swings["lows"]),
          f"lows={swings['lows'][:5]}")


def _reference_frame(rows):
    return (
        pd.Series([r["close"] for r in rows]),
        pd.Series([r["high"] for r in rows]),
        pd.Series([r["low"] for r in rows]),
    )


def test_pandas_crosscheck(rows):
    print("\n[5] 与 pandas 参照实现交叉验证（跳过前 60 根预热）")
    c, h, low = _reference_frame(rows)
    skip = 60
    # Wilder 平滑（RSI/ATR）我们用前 N 根 SMA 做种子，pandas 的 ewm(adjust=False)
    # 用首值做种子。alpha=1/14 时差异按 (13/14)^n 衰减，需要约 250 根才降到 1e-8，
    # 所以这两项从第 250 根起比对
    skip_wilder = 250

    # RSI (Wilder)
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    ref_rsi = 100 - 100 / (1 + gain / loss)
    err = max(abs(rows[i]["rsi14"] - ref_rsi[i]) for i in range(skip_wilder, len(rows)))
    check(f"RSI 最大误差 {err:.2e} < 1e-3", err < 1e-3)

    # ATR (Wilder)
    tr = pd.concat(
        [h - low, (h - c.shift()).abs(), (low - c.shift()).abs()], axis=1
    ).max(axis=1)
    ref_atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    err = max(abs(rows[i]["atr14"] - ref_atr[i]) for i in range(skip_wilder, len(rows)))
    check(f"ATR 最大误差 {err:.2e} < 1e-3", err < 1e-3)

    # KDJ
    llv = low.rolling(9).min()
    hhv = h.rolling(9).max()
    rsv = (c - llv) / (hhv - llv) * 100
    ref_k = rsv.fillna(50).ewm(alpha=1 / 3, adjust=False).mean()
    err = max(abs(rows[i]["k"] - ref_k[i]) for i in range(skip, len(rows)))
    check(f"KDJ-K 最大误差 {err:.2e} < 1e-2", err < 1e-2)

    # BOLL
    ref_mid = c.rolling(20).mean()
    ref_std = c.rolling(20).std(ddof=0)
    err_mid = max(abs(rows[i]["boll_mid"] - ref_mid[i]) for i in range(skip, len(rows)))
    err_up = max(
        abs(rows[i]["boll_upper"] - (ref_mid[i] + 2 * ref_std[i]))
        for i in range(skip, len(rows))
    )
    check(f"BOLL 中轨误差 {err_mid:.2e} < 1e-3", err_mid < 1e-3)
    check(f"BOLL 上轨误差 {err_up:.2e} < 1e-3", err_up < 1e-3)

    # MA
    ref_ma20 = c.rolling(20).mean()
    err = max(abs(rows[i]["ma20"] - ref_ma20[i]) for i in range(skip, len(rows)))
    check(f"MA20 最大误差 {err:.2e} < 1e-3", err < 1e-3)


def test_donchian_offbyone(rows):
    print("\n[6] 唐奇安通道 off-by-one")
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    # compute_donchian 输出 round(..., 4)，参照值也取整到同一精度再比，
    # 否则东财的高精度前复权价会稳定差出 5e-5（半个 ULP）的取整噪声。
    bad = []
    for i in range(60, len(rows)):
        if abs(rows[i]["dc20_upper"] - round(max(highs[i - 20 : i]), 4)) > 1e-6:
            bad.append(i)
        if abs(rows[i]["dc20_lower"] - round(min(lows[i - 20 : i]), 4)) > 1e-6:
            bad.append(i)
    check("dc20 用的是不含当根的前 20 根", not bad, f"异常下标 {bad[:5]}")

    breakouts = sum(
        1 for i in range(60, len(rows)) if rows[i]["close"] > rows[i]["dc20_upper"]
    )
    check(f"存在向上突破（{breakouts} 次），说明通道未把当根算进去", breakouts > 0)


def test_no_lookahead(rows):
    print("\n[7] 未来函数守卫：截断重算 vs 全量，逐根比对")
    fields = [
        "dif", "dea", "macd", "ma5", "ma20", "ma200", "rsi14", "k", "d", "j",
        "boll_mid", "boll_upper", "boll_lower", "boll_width", "boll_width_pct",
        "atr14", "dc20_upper", "dc20_lower", "dc55_upper", "dc55_lower",
    ]

    mismatches = []
    step = max(1, (len(rows) - 300) // 60)  # 抽样 60 个点，避免 O(n^2) 过慢
    for i in range(300, len(rows), step):
        raw = [
            {k: r[k] for k in ("date", "open", "high", "low", "close", "volume")}
            for r in rows[: i + 1]
        ]
        compute_macd(raw)
        compute_all_indicators(raw)

        for f in fields:
            a, b = raw[i].get(f), rows[i].get(f)
            if a is None and b is None:
                continue
            if a is None or b is None or abs(a - b) > 1e-6:
                mismatches.append((i, f, a, b))

    check(
        "所有指标在截断重算下保持一致（无未来函数）",
        not mismatches,
        f"前 3 处不一致 {mismatches[:3]}",
    )


def test_swing_confirmation(rows):
    print("\n[8] 摆动点确认延迟")
    full = find_swing_points(rows)
    truncated = find_swing_points(rows[:400])
    right = 3
    confirmed = [i for i in full["lows"] if i + right <= 399]
    check(
        "截断后已确认的摆动低点与全量一致",
        [i for i in truncated["lows"] if i + right <= 399] == confirmed,
    )


def main():
    print("=" * 60)
    print("技术指标验证")
    print("=" * 60)

    test_monotonic_up()
    test_monotonic_down()
    test_flat()
    test_v_shape()

    from services.stock_service import StockService

    print("\n拉取真实数据 600519 用于数值与未来函数校验...")
    real = StockService.get_historical_data("600519", "2018-01-01", "2026-12-31", "d")
    if not real or len(real) < 500:
        print("  跳过真实数据检查（数据不足）")
    else:
        print(f"  取得 {len(real)} 根K线")
        rows = copy.deepcopy(real)
        compute_macd(rows)
        compute_all_indicators(rows)
        test_pandas_crosscheck(rows)
        test_donchian_offbyone(rows)
        test_no_lookahead(rows)
        test_swing_confirmation(rows)

    print("\n" + "=" * 60)
    if FAILURES:
        print(f"失败 {len(FAILURES)} 项: {FAILURES}")
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
