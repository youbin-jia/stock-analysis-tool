"""财报快评服务

借鉴 Anthropic financial-services 仓库的 earnings analysis skill 思路：
- 拉取最新业绩快报 / 财务摘要
- 计算同比、环比变化
- 输出结构化"草稿点评"（明确标注为 draft，需人工复核）

数据源：腾讯财经的 web_stockinfo / 东方财富 datacenter（通过 akshare-style 直连），
为了不引入新依赖，这里采用东方财富的公开 HTTP 接口。
"""
from __future__ import annotations

import requests
from datetime import datetime
from typing import Optional, Dict, Any, List


def _eastmoney_secid(stock_code: str) -> str:
    """东方财富 secid: 1.600519 / 0.000858"""
    market = "1" if stock_code.startswith(("6", "9")) else "0"
    return f"{market}.{stock_code}"


def _safe_float(v) -> Optional[float]:
    try:
        if v in (None, "-", ""):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return (a - b) / abs(b) * 100.0


def fetch_financial_summary(stock_code: str, limit: int = 8) -> List[Dict[str, Any]]:
    """获取最近 N 期业绩摘要（按报告期倒序）

    使用东方财富公开数据接口：
    https://datacenter.eastmoney.com/securities/api/data/v1/get
    """
    secid = _eastmoney_secid(stock_code)
    url = (
        "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        "?reportName=RPT_LICO_FN_CPD"
        f"&columns=SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,"
        "BASIC_EPS,DEDUCT_BASIC_EPS,TOTAL_OPERATE_INCOME,"
        "PARENT_NETPROFIT,WEIGHTAVG_ROE,YSTZ,YSHZ,SJLTZ,SJLHZ"
        f"&filter=(SECURITY_CODE%3D%22{stock_code}%22)"
        f"&pageSize={limit}&pageNumber=1&sortColumns=REPORT_DATE&sortTypes=-1"
        "&source=WEB&client=WEB"
    )
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = (data.get("result") or {}).get("data") or []
        result = []
        for r in rows:
            result.append({
                "report_date": r.get("REPORT_DATE", "")[:10],
                "eps": _safe_float(r.get("BASIC_EPS")),
                "eps_deducted": _safe_float(r.get("DEDUCT_BASIC_EPS")),
                "revenue": _safe_float(r.get("TOTAL_OPERATE_INCOME")),
                "net_profit": _safe_float(r.get("PARENT_NETPROFIT")),
                "roe": _safe_float(r.get("WEIGHTAVG_ROE")),
                "revenue_yoy": _safe_float(r.get("YSTZ")),   # 营收同比
                "revenue_qoq": _safe_float(r.get("YSHZ")),   # 营收环比
                "profit_yoy": _safe_float(r.get("SJLTZ")),   # 净利同比
                "profit_qoq": _safe_float(r.get("SJLHZ")),   # 净利环比
            })
        # 附股票名称
        if rows:
            result_meta = {"name": rows[0].get("SECURITY_NAME_ABBR")}
        else:
            result_meta = {"name": None}
        return [{**r, "name": result_meta["name"]} for r in result]
    except Exception as e:
        print(f"[earnings] fetch_financial_summary error: {e}")
        return []


def build_earnings_snapshot(stock_code: str) -> Dict[str, Any]:
    """生成财报快评（draft）

    输出结构对齐 Anthropic IC memo / earnings analysis 风格：
        - headline
        - period
        - key_metrics（含同比环比）
        - trend（多期）
        - red_flags（自动识别风险点）
        - notes（人工复核提示）
    """
    history = fetch_financial_summary(stock_code, limit=8)
    if not history:
        return {
            "available": False,
            "code": stock_code,
            "message": "未获取到财务数据",
        }

    latest = history[0]
    prev = history[1] if len(history) > 1 else None

    # 自动识别 red flags（仅启发式，需人工复核）
    red_flags: List[str] = []
    if latest.get("profit_yoy") is not None and latest["profit_yoy"] < -20:
        red_flags.append(f"归母净利同比下滑 {latest['profit_yoy']:.1f}%，幅度超过 20%")
    if latest.get("revenue_yoy") is not None and latest["revenue_yoy"] < -10:
        red_flags.append(f"营业收入同比下滑 {latest['revenue_yoy']:.1f}%")
    if (latest.get("eps") is not None and latest.get("eps_deducted") is not None
            and latest["eps"] > 0 and latest["eps_deducted"] / latest["eps"] < 0.6):
        red_flags.append("扣非EPS/基本EPS < 60%，非经常性损益占比偏高，关注利润质量")
    if latest.get("roe") is not None and latest["roe"] < 5:
        red_flags.append(f"加权ROE仅 {latest['roe']:.2f}%，盈利能力偏弱")
    if prev and latest.get("revenue") and prev.get("revenue"):
        if latest["revenue"] < prev["revenue"] * 0.95:
            red_flags.append("营业收入环比下滑 5% 以上")

    # headline
    yoy = latest.get("profit_yoy")
    if yoy is None:
        headline = f"{latest.get('name') or stock_code} {latest['report_date']} 报告期业绩快评（draft）"
    elif yoy > 30:
        headline = f"{latest.get('name') or stock_code} 净利大幅增长 {yoy:.1f}%，关注可持续性（draft）"
    elif yoy > 0:
        headline = f"{latest.get('name') or stock_code} 净利同比 +{yoy:.1f}%，温和增长（draft）"
    else:
        headline = f"{latest.get('name') or stock_code} 净利同比 {yoy:.1f}%，承压（draft）"

    return {
        "available": True,
        "code": stock_code,
        "name": latest.get("name"),
        "headline": headline,
        "period": latest["report_date"],
        "key_metrics": {
            "revenue": latest.get("revenue"),
            "net_profit": latest.get("net_profit"),
            "eps": latest.get("eps"),
            "eps_deducted": latest.get("eps_deducted"),
            "roe": latest.get("roe"),
            "revenue_yoy": latest.get("revenue_yoy"),
            "profit_yoy": latest.get("profit_yoy"),
            "revenue_qoq": latest.get("revenue_qoq"),
            "profit_qoq": latest.get("profit_qoq"),
        },
        "trend": history,
        "red_flags": red_flags,
        "disclaimer": (
            "本快评由系统基于公开财务数据自动生成（draft），仅供研究参考，"
            "不构成投资建议。请人工复核数据准确性、识别非经常性影响，并结合业务基本面判断。"
        ),
        "generated_at": datetime.now().isoformat(),
    }
