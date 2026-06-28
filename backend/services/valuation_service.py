"""估值服务：DCF + Comps

借鉴 Anthropic financial-services 的 /dcf 和 /comps：
- DCF 不做"全自动估值"，所有假设由调用方传入，
  避免文章里批评的"硬编码假设、Assumptions 没链接"问题；
- Comps 使用东方财富同行业指标做横向对标，返回原始数据 + 中位数。
"""
from __future__ import annotations

import requests
from typing import Dict, Any, List, Optional


# ---------- DCF ----------

def run_dcf(
    fcf_base: float,                 # 基期自由现金流（亿元或万元，自洽即可）
    growth_rates: List[float],       # 显性预测期各年增长率（小数，如 0.10 = 10%）
    terminal_growth: float,          # 永续增长率 g（小数）
    wacc: float,                     # 折现率 WACC（小数）
    net_debt: float = 0.0,           # 净债务（与 fcf_base 同口径）
    shares_out: float = 1.0,         # 总股本（亿股 / 与 fcf_base 同口径）
) -> Dict[str, Any]:
    """两阶段 DCF。

    Returns:
        explicit_fcf: 显性预测期 FCF 序列
        explicit_pv:  各期 FCF 现值
        terminal_value: 终值
        terminal_pv:   终值现值
        enterprise_value: EV
        equity_value:     股权价值（EV - 净债务）
        per_share:        每股内在价值
        assumptions: 回显输入，便于审计
        warnings:    输入合理性提醒（学文章里 /debug-model 的精神）
    """
    if wacc <= terminal_growth:
        return {
            "ok": False,
            "error": "WACC 必须大于永续增长率 g，否则戈登模型分母 ≤ 0",
        }

    warnings: List[str] = []
    if terminal_growth > 0.05:
        warnings.append("永续增长率 > 5% 属于乐观假设，A 股大盘股长期一般 2%~3%")
    if wacc < 0.06 or wacc > 0.15:
        warnings.append(f"WACC={wacc:.2%} 偏离常见区间 8%~12%，请复核 β 和无风险利率")
    if any(g > 0.5 for g in growth_rates):
        warnings.append("显性期存在 >50% 的年增长率，建议拆分阶段或下调")
    if not (3 <= len(growth_rates) <= 10):
        warnings.append("显性预测期一般 5~10 年，过短或过长都会扭曲估值")

    # 显性预测 FCF
    fcfs: List[float] = []
    cur = fcf_base
    for g in growth_rates:
        cur = cur * (1 + g)
        fcfs.append(cur)

    # 各期 FCF 现值
    pvs = [fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs)]

    # 终值（Gordon growth）
    last_fcf = fcfs[-1]
    terminal_value = last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    terminal_pv = terminal_value / ((1 + wacc) ** len(fcfs))

    ev = sum(pvs) + terminal_pv
    equity_value = ev - net_debt
    per_share = equity_value / shares_out if shares_out > 0 else None

    return {
        "ok": True,
        "explicit_fcf": [round(x, 4) for x in fcfs],
        "explicit_pv": [round(x, 4) for x in pvs],
        "terminal_value": round(terminal_value, 4),
        "terminal_pv": round(terminal_pv, 4),
        "enterprise_value": round(ev, 4),
        "equity_value": round(equity_value, 4),
        "per_share": round(per_share, 4) if per_share is not None else None,
        "assumptions": {
            "fcf_base": fcf_base,
            "growth_rates": growth_rates,
            "terminal_growth": terminal_growth,
            "wacc": wacc,
            "net_debt": net_debt,
            "shares_out": shares_out,
        },
        "warnings": warnings,
        "disclaimer": "DCF 结果对假设极度敏感（draft），请做敏感性分析并人工复核。",
    }


def dcf_sensitivity(
    fcf_base: float,
    growth_rates: List[float],
    base_wacc: float,
    base_g: float,
    net_debt: float = 0.0,
    shares_out: float = 1.0,
    wacc_step: float = 0.01,
    g_step: float = 0.005,
) -> Dict[str, Any]:
    """敏感性表：WACC × 永续增长率 → 每股内在价值"""
    waccs = [round(base_wacc + i * wacc_step, 4) for i in range(-2, 3)]
    gs = [round(base_g + i * g_step, 4) for i in range(-2, 3)]
    matrix: List[List[Optional[float]]] = []
    for w in waccs:
        row: List[Optional[float]] = []
        for g in gs:
            r = run_dcf(fcf_base, growth_rates, g, w, net_debt, shares_out)
            row.append(r.get("per_share") if r.get("ok") else None)
        matrix.append(row)
    return {"wacc_axis": waccs, "g_axis": gs, "per_share_matrix": matrix}


# ---------- Comps ----------

def _safe_float(v) -> Optional[float]:
    try:
        if v in (None, "-", ""):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _median(nums: List[float]) -> Optional[float]:
    nums = [n for n in nums if n is not None]
    if not nums:
        return None
    nums = sorted(nums)
    n = len(nums)
    return nums[n // 2] if n % 2 else (nums[n // 2 - 1] + nums[n // 2]) / 2


def _fetch_board_code(stock_code: str) -> Optional[Dict[str, str]]:
    """从东方财富个股财务摘要表里拿 BOARD_NAME / BOARD_CODE"""
    url = (
        "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        "?reportName=RPT_LICO_FN_CPD&columns=SECURITY_CODE,BOARD_NAME,BOARD_CODE"
        f"&filter=(SECURITY_CODE%3D%22{stock_code}%22)"
        "&pageSize=1&pageNumber=1&sortColumns=NOTICE_DATE&sortTypes=-1"
        "&source=WEB&client=WEB"
    )
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        rows = ((r.json() or {}).get("result") or {}).get("data") or []
        if not rows:
            return None
        return {"industry": rows[0].get("BOARD_NAME"), "board_code": rows[0].get("BOARD_CODE")}
    except Exception as e:
        print(f"[comps] _fetch_board_code error: {e}")
        return None


def fetch_industry_peers(stock_code: str) -> Dict[str, Any]:
    """通过东方财富取目标公司所属行业的同行可比表（PE/PB/PS/ROE 等）"""
    try:
        meta = _fetch_board_code(stock_code)
        if not meta or not meta.get("board_code"):
            return {"available": False, "message": "无法识别所属行业板块"}
        industry = meta["industry"]
        board_code = meta["board_code"]

        # 用板块代码筛同行业（fs=b:BKxxxx）
        peers_url = (
            "https://push2.eastmoney.com/api/qt/clist/get"
            "?pn=1&pz=500&po=1&np=1&fltt=2&invt=2"
            f"&fs=b:{board_code}"
            "&fields=f12,f14,f2,f3,f9,f23,f37,f114"
        )
        resp2 = requests.get(peers_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        diff = ((resp2.json() or {}).get("data") or {}).get("diff") or []

        rows: List[Dict[str, Any]] = []
        for r in diff:
            rows.append({
                "code": r.get("f12"),
                "name": r.get("f14"),
                "price": _safe_float(r.get("f2")),
                "change_percent": _safe_float(r.get("f3")),
                "pe_ttm": _safe_float(r.get("f9")),
                "pb": _safe_float(r.get("f23")),
                "roe": _safe_float(r.get("f37")),
                "ps": _safe_float(r.get("f114")),
            })

        if not rows:
            return {"available": False, "industry": industry, "message": "未取到同行业成分股"}

        # 目标在前
        target = next((x for x in rows if x["code"] == stock_code), None)
        peers = [x for x in rows if x["code"] != stock_code]

        summary = {
            "median_pe": _median([x["pe_ttm"] for x in rows if x["pe_ttm"] and x["pe_ttm"] > 0]),
            "median_pb": _median([x["pb"] for x in rows if x["pb"] and x["pb"] > 0]),
            "median_ps": _median([x["ps"] for x in rows if x["ps"] and x["ps"] > 0]),
            "median_roe": _median([x["roe"] for x in rows if x["roe"] is not None]),
            "count": len(rows),
        }

        # 相对估值快速结论（draft）
        commentary: List[str] = []
        if target and target.get("pe_ttm") and summary["median_pe"]:
            diff_pct = (target["pe_ttm"] - summary["median_pe"]) / summary["median_pe"] * 100
            commentary.append(
                f"PE(TTM) {target['pe_ttm']:.1f} vs 行业中位 {summary['median_pe']:.1f}，相对 {diff_pct:+.1f}%"
            )
        if target and target.get("roe") is not None and summary["median_roe"] is not None:
            commentary.append(
                f"ROE {target['roe']:.2f}% vs 行业中位 {summary['median_roe']:.2f}%"
            )

        return {
            "available": True,
            "industry": industry,
            "target": target,
            "peers": peers[:30],
            "summary": summary,
            "commentary": commentary,
            "disclaimer": "可比公司分析仅基于行业划分和静态指标（draft），未做业务质量调整，请人工复核同行可比性。",
        }
    except Exception as e:
        print(f"[comps] error: {e}")
        return {"available": False, "message": str(e)}
