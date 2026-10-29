import math
import re
from datetime import datetime, time, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd
import requests

from services.cache_service import CacheService
from services.indicator_service import (
    compute_atr, compute_boll, compute_kdj, compute_ma, compute_macd, compute_rsi,
)

# 支持的指数：前端选择器与此保持一致
INDEX_MAP = {
    "sh000688": "科创50",
    "sh000001": "上证指数",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
    "sz399001": "深证成指",
    "sh000905": "中证500",
    "sh000852": "中证1000",
}

# 情景分位与展示名称
_QUANTILES = [
    ("p05", 0.05, "极端悲观"),
    ("p25", 0.25, "悲观"),
    ("p50", 0.50, "中性"),
    ("p75", 0.75, "乐观"),
    ("p95", 0.95, "极端乐观"),
]

# 标准正态分位数（对应上面的概率）
_Z = {0.05: -1.6449, 0.25: -0.6745, 0.50: 0.0, 0.75: 0.6745, 0.95: 1.6449}

TRADING_DAYS_PER_YEAR = 252
SHANGHAI = ZoneInfo("Asia/Shanghai")
REFRESH_SECONDS = 15
_HISTORY_LOCK = Lock()


class ScenarioService:
    """指数前瞻情景区间：基于历史已实现波动率的随机游走分位数锥。

    这不是预测。中枢路径按零漂移处理，区间宽度完全由历史波动率决定，
    表达的是"在过去的波动水平下，未来 N 个交易日价格有多大概率落在什么范围"。
    """

    @staticmethod
    def _now() -> datetime:
        return datetime.now(SHANGHAI)

    @staticmethod
    def _fetch_close(index_code: str, refresh: bool = False) -> Optional[pd.DataFrame]:
        # The provider's native JS decoder cannot initialize concurrently.
        with _HISTORY_LOCK:
            return ScenarioService._load_close(index_code, refresh=refresh)

    @staticmethod
    def _load_close(index_code: str, refresh: bool = False) -> Optional[pd.DataFrame]:
        cache_key = f"index_history:v2:{index_code}:{ScenarioService._now().date()}"
        cached = None if refresh else CacheService.get_cached_quant(cache_key)
        try:
            df = pd.DataFrame(cached) if cached else ak.stock_zh_index_daily(symbol=index_code)
            if df is None or df.empty:
                return None
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
            for field in ("open", "high", "low", "close"):
                df[field] = pd.to_numeric(df[field], errors="coerce")
            df = df.dropna(subset=["date", "open", "high", "low", "close"])
            df = df[df["close"].map(lambda value: math.isfinite(value) and value > 0)]
            df = df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
            if not cached and not df.empty:
                records = df[["date", "open", "high", "low", "close"]].copy()
                records["date"] = records["date"].dt.strftime("%Y-%m-%d")
                CacheService.set_cached_quant(cache_key, records.to_dict("records"), ttl=1800)
            return df
        except Exception as e:  # noqa: BLE001
            print(f"获取指数历史数据错误 {index_code}: {e}")
            return None

    @staticmethod
    def _fetch_quote(index_code: str) -> Optional[Dict[str, Any]]:
        """指数代码保留交易所前缀；成交量为手，成交额统一为元。"""
        if index_code not in INDEX_MAP:
            return None
        try:
            response = requests.get(f"https://qt.gtimg.cn/q={index_code}", timeout=8)
            response.raise_for_status()
            response.encoding = "gb2312"
            match = re.fullmatch(rf'v_{re.escape(index_code)}="([^"]*)";?', response.text.strip())
            if not match:
                return None
            parts = match.group(1).split("~")
            if len(parts) < 38 or parts[2] != index_code[2:]:
                return None
            price, prev_close, opening, high, low = (
                float(parts[i]) for i in (3, 4, 5, 33, 34)
            )
            if not all(math.isfinite(v) and v > 0 for v in (price, prev_close, opening, high, low)):
                return None
            timestamp = datetime.strptime(parts[30], "%Y%m%d%H%M%S").replace(tzinfo=SHANGHAI)

            def nonnegative(index):
                try:
                    value = float(parts[index])
                    return value if math.isfinite(value) and value >= 0 else None
                except ValueError:
                    return None

            amount = nonnegative(37)
            return {
                "price": price, "prev_close": prev_close, "open": opening,
                "high": high, "low": low, "volume": nonnegative(36),
                "amount": amount * 10000 if amount is not None else None,
                "change": round(price - prev_close, 2),
                "change_percent": round((price / prev_close - 1) * 100, 2),
                "amplitude": round((high - low) / prev_close * 100, 2),
                "timestamp": timestamp.isoformat(), "source": "腾讯财经",
            }
        except (requests.RequestException, ValueError, IndexError) as e:
            print(f"获取指数实时行情错误 {index_code}: {e}")
            return None

    @staticmethod
    def _quote_status(timestamp: datetime, now: datetime) -> str:
        during_session = now.weekday() < 5 and (
            time(9, 30) <= now.time() <= time(11, 30)
            or time(13) <= now.time() < time(15)
        )
        if during_session:
            return "live" if timedelta(0) <= now - timestamp <= timedelta(seconds=120) else "delayed"
        if (
            timestamp.date() == now.date()
            and timestamp.time() < time(15) <= now.time()
            and now - timestamp > timedelta(seconds=120)
        ):
            return "delayed"
        return "closed"

    @staticmethod
    def _forward_dates(last_date: pd.Timestamp, days: int) -> List[str]:
        """按自然日推进并跳过周末，生成未来交易日序列（不含法定节假日调整）。"""
        dates = []
        cur = last_date
        while len(dates) < days:
            cur = cur + pd.Timedelta(days=1)
            if cur.weekday() < 5:
                dates.append(cur.strftime("%Y-%m-%d"))
        return dates

    @staticmethod
    def get_scenario(
        index_code: str,
        forward_days: int = 42,
        vol_window: int = 60,
        history_days: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if index_code not in INDEX_MAP:
            return None
        now = ScenarioService._now()
        df = ScenarioService._fetch_close(index_code)
        if df is None:
            return None
        df = df[df["date"].dt.date <= now.date()].copy()
        if len(df) < vol_window + 2:
            return None

        quote = ScenarioService._fetch_quote(index_code)
        now = ScenarioService._now()
        if quote:
            quote = quote.copy()
            timestamp = datetime.fromisoformat(quote["timestamp"])
            quote_date = pd.Timestamp(timestamp.date())
            if quote_date < df["date"].iloc[-1] or timestamp > now:
                quote = None
            else:
                # Replace today's partial bar, never append a second bar for the same date.
                df = df[df["date"] != quote_date]
                df = pd.concat([df, pd.DataFrame([{
                    "date": quote_date, "open": quote["open"], "high": quote["high"],
                    "low": quote["low"], "close": quote["price"],
                }])], ignore_index=True)
                quote["status"] = ScenarioService._quote_status(timestamp, now)

        if quote is None:
            latest = df.iloc[-1]
            prev_close = float(df["close"].iloc[-2])
            quote = {
                "price": float(latest["close"]), "prev_close": prev_close,
                "open": float(latest["open"]), "high": float(latest["high"]),
                "low": float(latest["low"]), "volume": None, "amount": None,
                "change": round(float(latest["close"]) - prev_close, 2),
                "change_percent": round((float(latest["close"]) / prev_close - 1) * 100, 2),
                "amplitude": round((float(latest["high"]) - float(latest["low"])) / prev_close * 100, 2),
                "timestamp": None, "source": "历史日线", "status": "historical",
            }
        quote["date"] = df["date"].iloc[-1].strftime("%Y-%m-%d")
        quote["is_intraday"] = bool(
            quote["timestamp"]
            and quote["date"] == now.date().isoformat()
            and datetime.fromisoformat(quote["timestamp"]).time() < time(15)
        )

        # A partial daily return must not distort the realized daily-volatility estimate.
        completed = (
            df[df["date"].dt.date < now.date()]
            if now.time() < time(15) or quote["is_intraday"] else df
        )
        if len(completed) < vol_window + 1:
            return None

        close = df["close"].astype(float)
        last_price = float(close.iloc[-1])
        last_date = df["date"].iloc[-1]

        completed_close = completed["close"].astype(float)
        log_ret = (completed_close / completed_close.shift(1)).apply(math.log).dropna()
        daily_vol = float(log_ret.tail(vol_window).std())
        ann_vol = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)

        # Calculate from the earliest available bar so every view shares the same indicators.
        rows = df.to_dict("records")
        compute_ma(rows, (5, 10, 20, 60, 120, 250))
        compute_macd(rows)
        compute_rsi(rows)
        compute_kdj(rows)
        compute_boll(rows)
        compute_atr(rows)
        indicator_fields = (
            "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
            "dif", "dea", "macd", "rsi14", "k", "d", "j",
            "boll_upper", "boll_mid", "boll_lower", "atr14",
        )
        indicators = {field: rows[-1].get(field) for field in indicator_fields}

        history = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                **{field: round(float(row[field]), 2) for field in ("open", "close", "low", "high")},
                **{field: row.get(field) for field in indicator_fields},
            }
            for row in (rows if history_days is None else rows[-history_days:])
        ]

        forward_dates = ScenarioService._forward_dates(last_date, forward_days)
        paths: Dict[str, List[float]] = {key: [] for key, _, _ in _QUANTILES}
        for step in range(1, forward_days + 1):
            sigma_t = daily_vol * math.sqrt(step)
            for key, prob, _ in _QUANTILES:
                # 零漂移几何布朗运动，含 -0.5σ²t 的凸性修正
                drift = -0.5 * sigma_t ** 2
                paths[key].append(
                    round(last_price * math.exp(drift + _Z[prob] * sigma_t), 2)
                )

        scenarios = [
            {
                "key": key,
                "label": label,
                "probability": prob,
                "values": paths[key],
                "end_value": paths[key][-1],
                "end_change_pct": round((paths[key][-1] / last_price - 1) * 100, 2),
            }
            for key, prob, label in _QUANTILES
        ]

        levels = []
        for n in (20, 60, 120, 250):
            if len(close) >= n:
                ma = float(close.tail(n).mean())
                levels.append(
                    {
                        "name": f"MA{n}",
                        "value": round(ma, 2),
                        "distance_pct": round((last_price / ma - 1) * 100, 2),
                    }
                )
        two_year = close.tail(TRADING_DAYS_PER_YEAR * 2)
        two_year_high = float(two_year.max())
        two_year_low = float(two_year.min())
        levels.append(
            {
                "name": "两年高点",
                "value": round(two_year_high, 2),
                "distance_pct": round((last_price / two_year_high - 1) * 100, 2),
            }
        )
        levels.append(
            {
                "name": "两年低点",
                "value": round(two_year_low, 2),
                "distance_pct": round((last_price / two_year_low - 1) * 100, 2),
            }
        )

        return {
            "index_code": index_code,
            "index_name": INDEX_MAP.get(index_code, index_code),
            "last_price": round(last_price, 2),
            "last_date": last_date.strftime("%Y-%m-%d"),
            "forward_days": forward_days,
            "vol_window": vol_window,
            "annualized_vol": round(ann_vol * 100, 1),
            "history": history,
            "history_start": history[0]["date"],
            "history_count": len(history),
            "forward_dates": forward_dates,
            "scenarios": scenarios,
            "levels": levels,
            "quote": quote,
            "indicators": indicators,
            "volatility_as_of": completed["date"].iloc[-1].strftime("%Y-%m-%d"),
            "refresh_interval": REFRESH_SECONDS,
            "generated_at": now.isoformat(),
        }
