from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.thesis_service import (
    create_thesis, list_thesis, get_thesis, update_thesis,
    delete_thesis, check_thesis, check_all,
)

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


class ThesisCreate(BaseModel):
    code: str
    name: Optional[str] = None
    title: str = Field(..., description="一句话标题，如：白酒龙头估值修复")
    thesis: str = Field(..., description="完整投资逻辑")
    buy_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    horizon: Optional[str] = Field(None, description="持有周期，如 6-12 个月")
    triggers: Optional[List[str]] = Field(None, description="关键触发条件，如：Q3 净利同比转正")


class ThesisUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    thesis: Optional[str] = None
    buy_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    horizon: Optional[str] = None
    triggers: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="active / closed / invalidated")


@router.get("")
async def list_all(status: Optional[str] = None):
    return {"data": list_thesis(status=status)}


@router.post("")
async def create(payload: ThesisCreate):
    return create_thesis(payload.model_dump())


@router.get("/{tid}")
async def get_one(tid: int):
    t = get_thesis(tid)
    if not t:
        raise HTTPException(status_code=404, detail="thesis not found")
    return t


@router.patch("/{tid}")
async def update(tid: int, payload: ThesisUpdate):
    t = update_thesis(tid, {k: v for k, v in payload.model_dump().items() if v is not None})
    if not t:
        raise HTTPException(status_code=404, detail="thesis not found")
    return t


@router.delete("/{tid}")
async def delete(tid: int):
    ok = delete_thesis(tid)
    if not ok:
        raise HTTPException(status_code=404, detail="thesis not found")
    return {"ok": True}


@router.get("/{tid}/check")
async def check_one(tid: int):
    res = check_thesis(tid)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res


@router.get("/_/check-all")
async def check_all_route(status: str = "active"):
    return {"data": check_all(status=status)}
