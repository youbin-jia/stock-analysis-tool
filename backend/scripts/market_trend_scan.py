"""One-off scan: index trends + industry rotation over the past 1-2 years."""
import concurrent.futures as cf
import datetime as dt
import json

import akshare as ak
import pandas as pd

END = dt.date.today()
START = END - dt.timedelta(days=760)
S, E = START.strftime("%Y%m%d"), END.strftime("%Y%m%d")

INDEXES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "沪深300": "sh000300",
    "中证500": "sh000905",
    "中证1000": "sh000852",
    "科创50": "sh000688",
    "北证50": "bj899050",
}


def pct(a, b):
    return round((a / b - 1) * 100, 2)


def index_stats(name, code):
    df = ak.stock_zh_index_daily(symbol=code)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= pd.Timestamp(START)].reset_index(drop=True)
    if df.empty:
        return None
    c = df["close"]
    last = c.iloc[-1]

    def back(n):
        return pct(last, c.iloc[-n]) if len(c) > n else None

    ma = {f"MA{n}": round(c.tail(n).mean(), 2) for n in (20, 60, 120, 250) if len(c) >= n}
    hi, lo = c.max(), c.min()
    return {
        "name": name,
        "last": round(last, 2),
        "date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        "chg_1m": back(20),
        "chg_3m": back(60),
        "chg_6m": back(120),
        "chg_1y": back(250),
        "chg_2y": pct(last, c.iloc[0]),
        **ma,
        "above_MA250": bool(len(c) >= 250 and last > c.tail(250).mean()),
        "high_2y": round(hi, 2),
        "low_2y": round(lo, 2),
        "drawdown_from_high": pct(last, hi),
        "rally_from_low": pct(last, lo),
        "ann_vol": round(c.pct_change().std() * (252 ** 0.5) * 100, 1),
    }


def industry_stats(item):
    code, name = item
    try:
        df = ak.index_hist_sw(symbol=code, period="day")
        if df is None or df.empty:
            return None
        df["日期"] = pd.to_datetime(df["日期"])
        df = df[df["日期"] >= pd.Timestamp(START)]
        c = df["收盘"].astype(float).reset_index(drop=True)
        last = c.iloc[-1]

        def back(n):
            return pct(last, c.iloc[-n]) if len(c) > n else None

        return {
            "行业": name,
            "近1月": back(20),
            "近3月": back(60),
            "近6月": back(120),
            "近1年": back(250),
            "区间全程": pct(last, c.iloc[0]),
            "距区间高点": pct(last, c.max()),
        }
    except Exception as ex:  # noqa: BLE001
        return {"行业": name, "error": str(ex)[:60]}


def main():
    out = {"as_of": END.isoformat(), "window": f"{S}-{E}"}

    idx = []
    for n, c in INDEXES.items():
        try:
            r = index_stats(n, c)
            if r:
                idx.append(r)
        except Exception as ex:  # noqa: BLE001
            idx.append({"name": n, "error": str(ex)[:80]})
    out["indexes"] = idx

    sw = ak.sw_index_first_info()
    names = list(zip(sw["行业代码"].str.replace(".SI", "", regex=False), sw["行业名称"]))
    rows = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(industry_stats, names):
            if r:
                rows.append(r)
    out["industries"] = rows

    with open("scripts/market_trend_scan.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out["indexes"], ensure_ascii=False, indent=1))
    print(f"industries fetched: {len(rows)}")


if __name__ == "__main__":
    main()
