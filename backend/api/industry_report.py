"""行业研究报告 API（含 SSE 流式）"""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.industry_report_service import (
    PRESET_INDUSTRIES, PRESET_FOCUS_DIMS,
    stream_report, list_reports, get_report, delete_report,
)

router = APIRouter(prefix="/api/industry-report", tags=["industry-report"])


class GenerateRequest(BaseModel):
    industry: str = Field(..., description="行业名称，如：半导体 / AI 算力硬件")
    style: str = Field("data_driven", description="data_driven / logic_driven / stock_first")
    custom_requirement: Optional[str] = Field(None, description="自定义额外要求")
    focus_dims: Optional[List[str]] = Field(None, description="关注维度 key 列表（来自 /presets）")
    temperature: float = Field(0.6, ge=0.0, le=1.5)


@router.get("/presets")
async def get_presets():
    """获取预置行业 + 预置关注维度"""
    return {
        "industries": PRESET_INDUSTRIES,
        "focus_dims": PRESET_FOCUS_DIMS,
        "styles": [
            {"key": "data_driven", "name": "数据驱动"},
            {"key": "logic_driven", "name": "逻辑驱动"},
            {"key": "stock_first", "name": "个股优先"},
        ],
    }


@router.post("/generate")
async def generate(req: GenerateRequest):
    """流式生成行业报告（SSE）

    每行：data: {"type":"meta|delta|done|error", ...}\\n\\n
    """
    if not req.industry.strip():
        raise HTTPException(status_code=400, detail="industry 不能为空")

    def event_stream():
        for chunk in stream_report(
            industry=req.industry.strip(),
            style=req.style,
            custom_requirement=req.custom_requirement,
            focus_dims=req.focus_dims,
            temperature=req.temperature,
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭 nginx 缓冲
            "Connection": "keep-alive",
        },
    )


@router.get("/list")
async def list_all(limit: int = 50):
    return {"data": list_reports(limit=limit)}


@router.get("/{rid}")
async def get_one(rid: int):
    r = get_report(rid)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    return r


@router.delete("/{rid}")
async def delete_one(rid: int):
    ok = delete_report(rid)
    if not ok:
        raise HTTPException(status_code=404, detail="report not found")
    return {"ok": True}
