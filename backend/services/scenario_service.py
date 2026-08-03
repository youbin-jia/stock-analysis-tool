import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import akshare as ak
import pandas as pd

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


class ScenarioService:
    """指数前瞻情景区间：基于历史已实现波动率的随机游走分位数锥。

    这不是预测。中枢路径按零漂移处理，区间宽度完全由历史波动率决定，
    表达的是"在过去的波动水平下，未来 N 个交易日价格有多大概率落在什么范围"。
    """

    @staticmethod
    def _fetch_close(index_code: str) -> Optional[pd.DataFrame]:
        try:
            df = ak.stock_zh_index_daily(symbol=index_code)
        except Exception as e:  # noqa: BLE001
            print(f"获取指数历史数据错误 {index_code}: {e}")
            return None
        if df is None or df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)

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
        history_days: int = 120,
    ) -> Optional[Dict[str, Any]]:
        df = ScenarioService._fetch_close(index_code)
        if df is None or len(df) < vol_window + 2:
            return None

        close = df["close"].astype(float)
        last_price = float(close.iloc[-1])
        last_date = df["date"].iloc[-1]

        log_ret = (close / close.shift(1)).apply(math.log).dropna()
        daily_vol = float(log_ret.tail(vol_window).std())
        ann_vol = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)

        hist = df.tail(history_days)
        history = [
            {"date": d.strftime("%Y-%m-%d"), "close": round(float(c), 2)}
            for d, c in zip(hist["date"], hist["close"].astype(float))
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
            "forward_dates": forward_dates,
            "scenarios": scenarios,
            "levels": levels,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
