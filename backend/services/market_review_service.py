"""Completed-session index reviews. Rules describe conditions, not return forecasts."""

import math
from datetime import date, datetime, time

import pandas as pd
from sqlalchemy.dialects.sqlite import insert

from models.database import IndexCloseReview, SessionLocal
from services.cache_service import CacheService
from services.indicator_service import compute_all_indicators, compute_macd
from services.scenario_service import INDEX_MAP, SHANGHAI, ScenarioService
from services.strategy_service import STRATEGY_MAP

REVIEW_TIME = time(15, 30)
RULE_VERSION = 1
MIN_BARS = 65
DISCLAIMER = (
    "技术面条件参考，未结合你的持仓、投资期限及风险承受能力，不构成个性化投资建议。"
    "指数点位不是 ETF 的委托价格；不自动交易，不承诺收益。"
)


def build_close_review(index_code, source_rows):
    """Input contains only completed bars; indicators never read an unfinished bar."""
    if len(source_rows) < MIN_BARS:
        return None
    rows = [dict(row) for row in source_rows]
    for row in rows:
        values = [row.get(field) for field in ("open", "close", "low", "high")]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in values):
            return None
        opening, close, low, high = values
        if not low <= min(opening, close) <= max(opening, close) <= high:
            return None
    compute_macd(rows)
    compute_all_indicators(rows)
    last, previous = rows[-1], rows[-2]
    close, ma20, ma60 = last["close"], last["ma20"], last["ma60"]
    rising = ma20 > rows[-6]["ma20"]
    falling = ma20 < rows[-6]["ma20"]
    if close > ma20 > ma60 and rising:
        trend, label = "bullish", "技术面偏强"
        summary = "收盘站在 MA20、MA60 上方，MA20 高于五个交易日前；中期趋势偏强，但仍需防范回撤。"
        stance = "顺势观察，避免追高"
        holding = f"以 MA20 {ma20:,.2f} 为趋势观察位；后续收盘维持其上方时跟踪趋势，失守时评估降低风险敞口。"
        entry = f"等待回踩 MA20 {ma20:,.2f} 后收盘重新站稳，且 DIF 仍高于 DEA，再评估分批参与；不因单日上涨追入。"
        invalidation = f"若后续收盘跌破 MA20 {ma20:,.2f} 且 MA5 低于 MA20，偏强判断失效，暂停加仓并复核持仓风险。"
    elif close < ma20 < ma60 and falling:
        trend, label = "bearish", "技术面偏弱"
        summary = "收盘位于 MA20、MA60 下方，MA20 低于五个交易日前；中期趋势偏弱，反弹不等于趋势反转。"
        stance = "防守优先，等待转强"
        holding = f"若后续收盘继续位于 MA20 {ma20:,.2f} 下方，优先评估降低相关风险敞口，避免无条件摊低成本。"
        entry = f"保持观望；等待收盘重回 MA20 {ma20:,.2f} 上方、MA5 高于 MA20 且 DIF 高于 DEA，再重新评估。"
        invalidation = f"若收盘重回 MA60 {ma60:,.2f} 上方且 MA20 转为上行，偏弱判断需重评；不把超卖直接当作买点。"
    else:
        trend, label = "neutral", "震荡待确认"
        summary = "价格、均线位置或 MA20 斜率尚未同向；当前缺少一致的中期趋势条件。"
        stance = "控制暴露，等待确认"
        holding = "控制单一方向的风险暴露，避免在震荡中频繁追涨杀跌；按事先确定的风险预算复核持仓。"
        entry = f"等待收盘突破前 20 日高点 {last['dc20_upper']:,.2f}，同时站上 MA20、MA60，再评估趋势是否成立。"
        invalidation = f"若收盘跌破前 20 日低点 {last['dc20_lower']:,.2f}，区间假设失效，暂停试仓并重新评估。"

    evidence = []
    for key in ("ma_alignment", "macd_cross", "rsi_regime", "donchian_20"):
        strategy = STRATEGY_MAP[key]
        state = strategy.describe_state(rows, len(rows) - 1)
        if key == "macd_cross" and last["dif"] == last["dea"]:
            state = {"status": "neutral", "detail": "DIF 与 DEA 持平，尚无方向优势"}
        if key == "rsi_regime" and last["rsi14"] == 50:
            state = {"status": "neutral", "detail": "RSI 位于 50，强弱中性"}
        signal = strategy.evaluate(rows, len(rows) - 1)
        evidence.append({
            "key": key, "name": strategy.name, **state,
            "signal": signal["reason"] if signal else None,
        })

    levels = []
    for key, name in (("ma20", "MA20"), ("ma60", "MA60"),
                      ("dc20_upper", "前20日高点"), ("dc20_lower", "前20日低点")):
        value = last[key]
        levels.append({
            "name": name, "value": round(value, 2),
            "role": "支撑观察" if value < close else "阻力观察" if value > close else "当前附近",
        })
    risks = []
    rsi = last["rsi14"]
    if rsi >= 70:
        risks.append(f"RSI(14) 为 {rsi:.1f}，短线偏热；强趋势中仍可能延续，不能单独作为卖出信号。")
    elif rsi <= 30:
        risks.append(f"RSI(14) 为 {rsi:.1f}，处于超卖区域；超卖不等于见底，不据此直接抄底。")
    momentum = evidence[1]["status"]
    if trend in ("bullish", "bearish") and momentum not in (trend, "neutral"):
        risks.append("均线趋势与 MACD 动能方向不一致，等待后续收盘确认，不因单一指标加大风险暴露。")
    risks.extend([
        "跳空、流动性与滑点可能使实际成交偏离观察位；观察位不是保证成交的止损价。",
        "未纳入估值、基本面、政策新闻及资金流；本规则未给出样本外胜率或收益预测。",
    ])
    return {
        "rule_version": RULE_VERSION,
        "index_code": index_code, "index_name": INDEX_MAP[index_code],
        "trade_date": last["date"], "close": round(close, 2),
        "change_percent": round((close / previous["close"] - 1) * 100, 2),
        "change_5d": round((close / rows[-6]["close"] - 1) * 100, 2),
        "atr14": last["atr14"], "atr_percent": round(last["atr14"] / close * 100, 2),
        "trend": trend, "verdict": label, "summary": summary, "stance": stance,
        "evidence": evidence, "levels": levels,
        "strategies": [
            {"title": "已有相关持仓", "detail": holding},
            {"title": "尚未持仓", "detail": entry},
            {"title": "判断失效条件", "detail": invalidation},
        ],
        "risks": risks,
        "methodology": (
            "偏强：收盘 > MA20 > MA60，且 MA20 高于五个交易日前；偏弱：上述条件反向成立；"
            "其余归为震荡。MACD、RSI 与前20日通道用于交叉核验，不换算上涨概率。"
            "全部条件以完成日线判断，不视为按当日收盘价成交的信号。"
        ),
        "disclaimer": DISCLAIMER,
    }


class MarketReviewService:
    @staticmethod
    def _now():
        return datetime.now(SHANGHAI)

    @staticmethod
    def _latest(index_code):
        with SessionLocal() as db:
            record = db.query(IndexCloseReview).filter(
                IndexCloseReview.index_code == index_code
            ).order_by(IndexCloseReview.trade_date.desc()).first()
            return record.payload if record else None

    @staticmethod
    def _save(report):
        statement = insert(IndexCloseReview).values(
            index_code=report["index_code"],
            trade_date=date.fromisoformat(report["trade_date"]),
            payload=report,
        ).on_conflict_do_update(
            index_elements=["index_code", "trade_date"],
            set_={"payload": report},
        )
        with SessionLocal() as db:
            db.execute(statement)
            db.commit()

    @staticmethod
    def _closed_rows(index_code, now):
        after_review_time = now.weekday() < 5 and now.time() >= REVIEW_TIME
        frame = ScenarioService._fetch_close(index_code, refresh=after_review_time)
        if frame is None or frame.empty:
            return None, None
        # A cached current-day bar can be partial. It is eligible only after a fresh
        # post-close history fetch, or an explicitly timestamped closing quote.
        completed = frame[frame["date"].dt.date < now.date()].copy()
        source = "历史日线"
        if after_review_time:
            today = frame[frame["date"].dt.date == now.date()]
            quote = ScenarioService._fetch_quote(index_code)
            timestamp = datetime.fromisoformat(quote["timestamp"]) if quote else None
            if timestamp and (
                timestamp.date() == now.date() and time(15) <= timestamp.time()
                and timestamp <= now
            ):
                today = pd.DataFrame([{
                    "date": pd.Timestamp(now.date()), "open": quote["open"],
                    "close": quote["price"], "low": quote["low"], "high": quote["high"],
                }])
                source = f"{quote['source']}收盘行情"
            elif timestamp and timestamp.date() == now.date() and timestamp.time() < time(15):
                today = today.iloc[0:0]
            elif not today.empty:
                source = "收盘后更新的历史日线"
            if not today.empty:
                completed = pd.concat([completed, today], ignore_index=True)
        rows = [
            {"date": row["date"].strftime("%Y-%m-%d"),
             **{field: float(row[field]) for field in ("open", "close", "low", "high")}}
            for row in completed.to_dict("records")
        ]
        return rows, source

    @staticmethod
    def get_review(index_code, refresh=False):
        if index_code not in INDEX_MAP:
            raise ValueError("不支持的指数代码")
        now = MarketReviewService._now()
        cache_key = f"close_review:v{RULE_VERSION}:{index_code}:{now.date()}"
        cached = None if refresh else CacheService.get_cached_quant(cache_key)
        if cached:
            return cached
        stored = MarketReviewService._latest(index_code)
        report = stored
        error = None
        try:
            rows, source = MarketReviewService._closed_rows(index_code, now)
            candidate = build_close_review(index_code, rows) if rows else None
            if candidate:
                candidate["source"] = source
                if not stored or candidate["trade_date"] >= stored["trade_date"]:
                    previous = {key: value for key, value in (stored or {}).items() if key != "generated_at"}
                    if candidate != previous:
                        candidate["generated_at"] = now.isoformat()
                        MarketReviewService._save(candidate)
                        report = candidate
            elif rows is not None:
                error = "完整日线不足或数据校验未通过，暂不生成新的策略结论。"
            else:
                error = "收盘数据获取失败，已保留最近一次复盘。"
        except Exception as exc:
            print(f"生成指数收盘复盘错误 {index_code}: {exc}")
            error = "复盘更新失败，已保留最近一次复盘。"

        if report and report["trade_date"] == now.date().isoformat():
            state, message = "ready", "当日收盘复盘已生成。"
        elif now.weekday() < 5 and now.time() < REVIEW_TIME:
            state, message = "waiting_close", "今日复盘待收盘后更新，当前仅使用已完成日线。"
        else:
            state, message = "pending_data", "暂无更新的已确认收盘数据，保留最近可用复盘；休市日不生成新报告。"
        result = {
            "index_code": index_code, "state": state, "message": message,
            "report": report, "error": error, "checked_at": now.isoformat(),
            "schedule": "北京时间 15:30；16:30、17:30 补查",
        }
        CacheService.set_cached_quant(cache_key, result, ttl=60)
        return result
