from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from data.books import (
    get_all_books,
    get_book_by_id,
    get_all_schools,
    get_all_tags,
    get_all_principles,
    get_all_quant_rules,
)

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/")
async def list_books(
    school: Optional[str] = Query(None, description="按流派筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    keyword: Optional[str] = Query(None, description="书名/作者关键词"),
):
    """获取书籍列表"""
    books = get_all_books()
    if school:
        books = [b for b in books if b["school"] == school]
    if tag:
        books = [b for b in books if tag in b["tags"]]
    if keyword:
        kw = keyword.lower()
        books = [
            b for b in books
            if kw in b["title"].lower()
            or kw in b["title_en"].lower()
            or kw in b["author"].lower()
        ]
    return books


@router.get("/schools")
async def list_schools():
    """获取所有流派"""
    return get_all_schools()


@router.get("/tags")
async def list_tags():
    """获取所有标签及出现次数"""
    return get_all_tags()


@router.get("/principles")
async def list_principles(
    school: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    """获取所有核心经验，用于统一查看/搜索"""
    principles = get_all_principles()
    if school:
        principles = [p for p in principles if p["school"] == school]
    if keyword:
        kw = keyword.lower()
        principles = [
            p for p in principles
            if kw in p["title"].lower()
            or kw in p["content"].lower()
            or kw in p["actionable"].lower()
        ]
    return principles


@router.get("/quant-rules")
async def list_quant_rules():
    """获取所有可量化规则"""
    return get_all_quant_rules()


@router.get("/{book_id}")
async def get_book(book_id: str):
    """获取书籍详情"""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return book
