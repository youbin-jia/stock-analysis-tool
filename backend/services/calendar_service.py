"""催化剂日历服务

借鉴 Anthropic equity-research 的 catalyst-calendar：
- 财报披露日（业绩预告/快报/正式）
- 分红/送转登记日
- 限售解禁日

数据来自东方财富 datacenter 公开接口。
"""
from __future__ import annotations

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def _safe(v):
    if v in (None, "-", ""):
        return None
    return v


def _get_em(report_name: str, columns: str, filters: str,
            sort_col: str = "NOTICE_DATE", page_size: int = 100) -> List[Dict]:
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        f"?reportName={report_name}&columns={columns}"
        f"&filter={filters}&pageSize={page_size}&pageNumber=1"
        f"&sortColumns={sort_col}&sortTypes=1"
        "&source=WEB&client=WEB"
    )
    try:
        resp = requests.get(
            url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://data.eastmoney.com/"},
        )
        return ((resp.json() or {}).get("result") or {}).get("data") or []
    except Exception as e:
        print(f"[calendar] {report_name} error: {e}")
        return []


def earnings_calendar(days_ahead: int = 30, code: Optional[str] = None) -> List[Dict[str, Any]]:
    """财报披露日历（预约披露）"""
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    filters = f"(APPOINT_PUBLISH_DATE%3E%3D%27{today}%27)(APPOINT_PUBLISH_DATE%3C%3D%27{end}%27)"
    if code:
        filters += f"(SECURITY_CODE%3D%22{code}%22)"
    rows = _get_em(
        "RPT_PUBLIC_BS_APPOIN",
        "SECURITY_CODE,SECURITY_NAME_ABBR,APPOINT_PUBLISH_DATE,REPORT_DATE,REPORT_TYPE_NAME",
        filters,
        sort_col="APPOINT_PUBLISH_DATE",
    )
    return [
        {
            "type": "earnings",
            "date": (r.get("APPOINT_PUBLISH_DATE") or "")[:10],
            "code": r.get("SECURITY_CODE"),
            "name": r.get("SECURITY_NAME_ABBR"),
            "title": f"{r.get('REPORT_TYPE_NAME') or (r.get('REPORT_DATE','')[:10] + ' 报告')} 披露",
        }
        for r in rows
    ]


def dividend_calendar(days_ahead: int = 60, code: Optional[str] = None) -> List[Dict[str, Any]]:
    """分红送转日历（除权除息日）"""
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    filters = f"(EX_DIVIDEND_DATE%3E%3D%27{today}%27)(EX_DIVIDEND_DATE%3C%3D%27{end}%27)"
    if code:
        filters += f"(SECURITY_CODE%3D%22{code}%22)"
    rows = _get_em(
        "RPT_SHAREBONUS_DET",
        "SECURITY_CODE,SECURITY_NAME_ABBR,EX_DIVIDEND_DATE,PLAN_EXPLAIN",
        filters,
        sort_col="EX_DIVIDEND_DATE",
    )
    return [
        {
            "type": "dividend",
            "date": (r.get("EX_DIVIDEND_DATE") or "")[:10],
            "code": r.get("SECURITY_CODE"),
            "name": r.get("SECURITY_NAME_ABBR"),
            "title": f"除权除息：{_safe(r.get('PLAN_EXPLAIN')) or '—'}",
        }
        for r in rows
    ]


def unlock_calendar(days_ahead: int = 60, code: Optional[str] = None) -> List[Dict[str, Any]]:
    """限售解禁日历（暂不可用：东方财富 reportName 未定位）"""
    return []


def upcoming_calendar(days_ahead: int = 30) -> Dict[str, Any]:
    """市场层面：未来 N 天全市场催化剂汇总"""
    earnings = earnings_calendar(days_ahead=days_ahead)
    dividends = dividend_calendar(days_ahead=days_ahead)
    unlocks = unlock_calendar(days_ahead=days_ahead)
    events = sorted(
        earnings + dividends + unlocks,
        key=lambda e: e.get("date") or "",
    )
    return {
        "days_ahead": days_ahead,
        "count": len(events),
        "events": events,
        "by_type": {
            "earnings": len(earnings),
            "dividend": len(dividends),
            "unlock": len(unlocks),
        },
        "disclaimer": "事件数据来自公开披露平台（draft），可能存在更正或延期，请以交易所最新公告为准。",
    }


def stock_calendar(code: str, days_ahead: int = 180) -> Dict[str, Any]:
    """个股层面：未来 N 天与该股有关的全部事件"""
    events = (
        earnings_calendar(days_ahead=days_ahead, code=code)
        + dividend_calendar(days_ahead=days_ahead, code=code)
        + unlock_calendar(days_ahead=days_ahead, code=code)
    )
    events.sort(key=lambda e: e.get("date") or "")
    return {
        "code": code,
        "days_ahead": days_ahead,
        "count": len(events),
        "events": events,
    }
