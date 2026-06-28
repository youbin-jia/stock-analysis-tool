"""投资观点跟踪服务（Thesis Tracker）

借鉴 Anthropic equity-research 的 thesis-tracker：
- 用户记录每笔持仓/关注股的"投资逻辑、买入价、目标价、止损价、关键触发条件"
- 系统自动按实时价检查目标价/止损是否触发
- 输出标准化的"复核清单"，强化 IC memo 风格的事后复盘

为避免改动现有 models/database.py，本模块用独立 SQLite 文件 data/thesis.db。
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.stock_service import StockService

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "thesis.db")


def init_thesis_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS thesis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                title TEXT NOT NULL,
                thesis TEXT NOT NULL,
                buy_price REAL,
                target_price REAL,
                stop_loss REAL,
                horizon TEXT,
                triggers_json TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def _conn():
    init_thesis_db()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["triggers"] = json.loads(d.pop("triggers_json") or "[]")
    except json.JSONDecodeError:
        d["triggers"] = []
    return d


def create_thesis(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO thesis(code,name,title,thesis,buy_price,target_price,stop_loss,
                               horizon,triggers_json,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["code"],
                payload.get("name"),
                payload["title"],
                payload["thesis"],
                payload.get("buy_price"),
                payload.get("target_price"),
                payload.get("stop_loss"),
                payload.get("horizon"),
                json.dumps(payload.get("triggers") or [], ensure_ascii=False),
                payload.get("status", "active"),
                now,
                now,
            ),
        )
        c.commit()
        tid = cur.lastrowid
    return get_thesis(tid)


def list_thesis(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM thesis WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM thesis ORDER BY created_at DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_thesis(tid: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM thesis WHERE id=?", (tid,)).fetchone()
    return _row_to_dict(row) if row else None


def update_thesis(tid: int, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cur = get_thesis(tid)
    if not cur:
        return None
    allowed = {"name", "title", "thesis", "buy_price", "target_price",
               "stop_loss", "horizon", "status"}
    sets, vals = [], []
    for k, v in patch.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    if "triggers" in patch:
        sets.append("triggers_json=?")
        vals.append(json.dumps(patch["triggers"] or [], ensure_ascii=False))
    if not sets:
        return cur
    sets.append("updated_at=?")
    vals.append(datetime.now().isoformat())
    vals.append(tid)
    with _conn() as c:
        c.execute(f"UPDATE thesis SET {','.join(sets)} WHERE id=?", vals)
        c.commit()
    return get_thesis(tid)


def delete_thesis(tid: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM thesis WHERE id=?", (tid,))
        c.commit()
        return cur.rowcount > 0


def check_thesis(tid: int) -> Dict[str, Any]:
    """对单条观点跑触发条件检查"""
    t = get_thesis(tid)
    if not t:
        return {"ok": False, "message": "thesis not found"}

    realtime = StockService.get_realtime_data(t["code"])
    if not realtime:
        return {"ok": False, "message": "未获取到实时行情"}
    price = realtime["price"]

    signals: List[str] = []
    if t.get("target_price") and price >= t["target_price"]:
        signals.append(f"已触达目标价 {t['target_price']}，当前 {price}")
    if t.get("stop_loss") and price <= t["stop_loss"]:
        signals.append(f"已击穿止损价 {t['stop_loss']}，当前 {price}")
    if t.get("buy_price") and t["buy_price"] > 0:
        ret = (price - t["buy_price"]) / t["buy_price"] * 100
        signals.append(f"相对买入价收益 {ret:+.2f}%")

    return {
        "ok": True,
        "id": tid,
        "code": t["code"],
        "name": t.get("name") or realtime.get("name"),
        "current_price": price,
        "buy_price": t.get("buy_price"),
        "target_price": t.get("target_price"),
        "stop_loss": t.get("stop_loss"),
        "signals": signals,
        "triggers": t.get("triggers", []),
        "checked_at": datetime.now().isoformat(),
    }


def check_all(status: str = "active") -> List[Dict[str, Any]]:
    return [check_thesis(t["id"]) for t in list_thesis(status=status)]
