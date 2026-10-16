"""策略回测验证脚本

三件事：
1. 打印各品种 × 各策略的胜率/样本数/平均收益
2. 与「随机信号」基线对照 —— 牛市样本里随机进场也能有 65% 胜率，
   脱离基线谈胜率没有意义，这个数字是整个功能诚实性的锚点
3. 哨兵检查：样本充足却胜率异常高，通常意味着有未来函数

用法：cd backend && ./venv/bin/python scripts/verify_backtest.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.indicator_service import compute_all_indicators, compute_macd
from services.stock_service import StockService
from services.strategy_service import (
    STRATEGIES,
    Strategy,
    backtest_strategy,
    compute_composite,
    compute_risk_levels,
    strategy_weight,
)

SYMBOLS = [
    ("600519", "贵州茅台/白马"),
    ("300750", "宁德时代/成长"),
    ("000001", "平安银行/金融"),
    ("510300", "沪深300ETF/宽基"),
    ("688981", "中芯国际/科创"),
]

FAILURES = []
WARNINGS = []


def _random_eval(rows, i):
    """无技能基线：用日期哈希产生与价格无关的信号"""
    h = hash(rows[i]["date"])
    if h % 20 == 0:
        return {"signal": "buy", "strength": 1.0, "reason": "随机基线"}
    if h % 20 == 1:
        return {"signal": "sell", "strength": 1.0, "reason": "随机基线"}
    return None


RANDOM_STRATEGY = Strategy(
    "random_baseline", "随机基线", "baseline", 25, _random_eval,
    lambda rows, i: {"status": "neutral", "detail": ""},
)


def load(code):
    rows = StockService.get_historical_data(code, "2016-01-01", "2026-12-31", "d")
    if not rows or len(rows) < 400:
        return None
    compute_macd(rows)
    compute_all_indicators(rows)
    return rows


def main():
    print("=" * 96)
    print("策略回测验证（持有 20 根，进场=信号次日收盘）")
    print("=" * 96)

    for code, label in SYMBOLS:
        rows = load(code)
        if not rows:
            print(f"\n{code} {label}: 数据不足，跳过")
            continue

        print(f"\n{code} {label}  共 {len(rows)} 根K线  {rows[0]['date']} ~ {rows[-1]['date']}")

        base = backtest_strategy(rows, RANDOM_STRATEGY, 20, "buy")
        print(f"  {'随机基线(无技能)':<20} n={base.signal_count:>3}  "
              f"胜率={base.win_rate:>6.1%}  均收益={base.avg_return:>7.2f}%")
        print(f"  {'-' * 88}")
        print(f"  {'策略':<20} {'n':>4} {'胜率':>8} {'均收益':>9} {'期望':>8} "
              f"{'权重':>6}  {'样本质量':>8}")

        for s in STRATEGIES:
            if s.key == "ma200_regime":
                continue
            st = backtest_strategy(rows, s, 20, "buy")
            if st.signal_count == 0:
                print(f"  {s.name:<20} {'-':>4} {'无买入信号':>10}")
                continue

            w = strategy_weight(st)
            edge = st.win_rate - base.win_rate
            flag = ""
            if st.signal_count > 15 and st.win_rate > 0.85:
                flag = "  <== SUSPICIOUS(疑似未来函数)"
                WARNINGS.append(f"{code}/{s.key} 胜率 {st.win_rate:.1%} n={st.signal_count}")

            print(f"  {s.name:<20} {st.signal_count:>4} {st.win_rate:>8.1%} "
                  f"{st.avg_return:>8.2f}% {st.expectancy:>7.2f}% {w:>6.2f}  "
                  f"{st.sample_quality:>8}  超基线{edge:+.1%}{flag}")

            # 内部一致性
            expect = st.win_rate * st.avg_win + (1 - st.win_rate) * st.avg_loss
            if abs(expect - st.expectancy) > 1e-6:
                FAILURES.append(f"{code}/{s.key} expectancy 不自洽")

        composite = compute_composite(
            rows, STRATEGIES,
            {s.key: {"buy": backtest_strategy(rows, s, 20, "buy"),
                     "sell": backtest_strategy(rows, s, 20, "sell")}
             for s in STRATEGIES if s.key != "ma200_regime"},
            "d",
        )
        risk = compute_risk_levels(rows)
        print(f"  → 综合: {composite['verdict']} 置信度 {composite['confidence']} "
              f"(net={composite['net_score']}, 触发 {len(composite['reasons'])} 个策略)")
        print(f"     市场状态: {composite['regime']['detail']}")
        if risk:
            print(f"     风控: 止损 {risk['stop_loss']} ({risk['stop_loss_pct']}%) / "
                  f"止盈 {risk['take_profit']} ({risk['take_profit_pct']}%)")

        if not 0 <= composite["confidence"] <= 100:
            FAILURES.append(f"{code} confidence 越界")
        if composite["verdict"] not in ("买入", "观望", "卖出"):
            FAILURES.append(f"{code} verdict 非法")

    print("\n" + "=" * 96)
    if WARNINGS:
        print(f"可疑项 {len(WARNINGS)}: {WARNINGS}")
    if FAILURES:
        print(f"失败 {len(FAILURES)}: {FAILURES}")
        sys.exit(1)
    print("全部通过" + ("（含可疑项，需人工复核）" if WARNINGS else ""))


if __name__ == "__main__":
    main()
