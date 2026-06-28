from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.valuation_service import run_dcf, dcf_sensitivity, fetch_industry_peers

router = APIRouter(prefix="/api/valuation", tags=["valuation"])


class DCFRequest(BaseModel):
    fcf_base: float = Field(..., description="基期自由现金流（亿元）")
    growth_rates: List[float] = Field(..., description="显性预测期年增长率序列，如 [0.10,0.10,0.08,0.06,0.04]")
    terminal_growth: float = Field(0.025, description="永续增长率 g")
    wacc: float = Field(0.09, description="折现率 WACC")
    net_debt: float = Field(0.0, description="净债务（亿元）")
    shares_out: float = Field(1.0, description="总股本（亿股）")


class DCFSensitivityRequest(DCFRequest):
    wacc_step: float = 0.01
    g_step: float = 0.005


@router.post("/dcf")
async def dcf(req: DCFRequest):
    """DCF 估值（引导式：所有假设必须显式传入）"""
    result = run_dcf(
        fcf_base=req.fcf_base,
        growth_rates=req.growth_rates,
        terminal_growth=req.terminal_growth,
        wacc=req.wacc,
        net_debt=req.net_debt,
        shares_out=req.shares_out,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/dcf/sensitivity")
async def dcf_sens(req: DCFSensitivityRequest):
    """DCF 敏感性表（WACC × g → 每股价值）"""
    return dcf_sensitivity(
        fcf_base=req.fcf_base,
        growth_rates=req.growth_rates,
        base_wacc=req.wacc,
        base_g=req.terminal_growth,
        net_debt=req.net_debt,
        shares_out=req.shares_out,
        wacc_step=req.wacc_step,
        g_step=req.g_step,
    )


@router.get("/comps/{code}")
async def comps(code: str):
    """同行业可比公司分析"""
    res = fetch_industry_peers(code)
    if not res.get("available"):
        raise HTTPException(status_code=404, detail=res.get("message", "未取到可比数据"))
    return res
