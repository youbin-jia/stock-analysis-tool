"""行业研究报告生成服务

参考"7步框架"（宏观→景气→研报→龙头→资金→估值→催化剂）写 Prompt 模板，
调用 Kimi（与 policy_service 共享 API Key），支持流式输出 + SQLite 持久化。
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import requests

# ---------- Kimi 配置（复用 policy_service 同套 env） ----------
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE = "https://api.moonshot.cn/v1"
KIMI_MODEL = os.environ.get("KIMI_REPORT_MODEL", "moonshot-v1-128k")

# ---------- DB ----------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "industry_report.db")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS industry_report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry TEXT NOT NULL,
                style TEXT,
                custom_requirement TEXT,
                focus_dims_json TEXT,
                content TEXT NOT NULL,
                model TEXT,
                tokens INTEGER,
                duration_ms INTEGER,
                status TEXT NOT NULL DEFAULT 'completed',
                created_at TEXT NOT NULL
            )
        """)
        c.commit()


@contextmanager
def _conn():
    init_db()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


# ---------- 预置行业 ----------
PRESET_INDUSTRIES: List[Dict[str, str]] = [
    {"key": "ai_compute", "name": "AI 算力硬件", "desc": "PCB / CCL / 光模块 / 服务器 / HBM / 液冷"},
    {"key": "semiconductor", "name": "半导体", "desc": "设备 / 材料 / 设计 / 制造 / 存储"},
    {"key": "innovative_drug", "name": "创新药", "desc": "License-out / CXO / ADC / GLP-1"},
    {"key": "low_altitude", "name": "低空经济 / 商业航天", "desc": "eVTOL / 商业火箭 / 商航外发制"},
    {"key": "robotics", "name": "人形机器人", "desc": "丝杠 / 减速器 / 电机 / 灵巧手"},
    {"key": "power_grid", "name": "电力 / 高股息", "desc": "水电 / 火电 / 电网投资"},
    {"key": "military", "name": "军工", "desc": "航发 / 卫星 / 信息化"},
    {"key": "new_energy_vehicle", "name": "新能源汽车", "desc": "整车 / 三电 / 智能驾驶"},
    {"key": "solar", "name": "光伏", "desc": "硅料 / 组件 / 储能 / BC 电池"},
    {"key": "consumer", "name": "大消费", "desc": "白酒 / 食品饮料 / 化妆品 / 服务消费"},
    {"key": "internet_china", "name": "中概互联", "desc": "港股科技 / 平台经济"},
    {"key": "cyclical", "name": "周期 / 资源", "desc": "有色 / 化工 / 煤炭 / 油气"},
]

PRESET_FOCUS_DIMS: List[Dict[str, str]] = [
    {"key": "macro",       "name": "宏观与政策"},
    {"key": "prosperity",  "name": "行业景气度（供需/价格/库存）"},
    {"key": "leaders",     "name": "龙头公司经营情况"},
    {"key": "capital",     "name": "资金面（ETF/北向/融资）"},
    {"key": "valuation",   "name": "估值与历史分位"},
    {"key": "catalyst",    "name": "催化剂与日历"},
    {"key": "risk",        "name": "风险与证伪信号"},
    {"key": "stock_map",   "name": "标的图谱（核心/弹性/观察）"},
    {"key": "tracking",    "name": "行业跟踪表（评分卡）"},
]


# ---------- Prompt 模板 ----------

def _build_prompt(
    industry: str,
    style: str,
    custom_requirement: Optional[str],
    focus_dims: Optional[List[str]],
) -> str:
    """根据 7 步研究框架构造结构化 Prompt"""
    style_hint = {
        "data_driven": "数据驱动型：每个结论必须有具体数字、表格、数据源（如 WSTS、TrendForce、Wind、东方财富），避免主观形容词。",
        "logic_driven": "逻辑驱动型：重逻辑推演与驱动因素拆解，数据作为证据点缀。需明确给出可证伪的关键假设。",
        "stock_first": "个股优先型：在标的图谱部分加重详细的成代检查表、业务拆解、估值与催化剂。",
    }.get(style, "数据驱动型")

    # 选中的章节
    dim_map = {d["key"]: d["name"] for d in PRESET_FOCUS_DIMS}
    selected = [dim_map[k] for k in (focus_dims or []) if k in dim_map] or list(dim_map.values())
    selected_text = "、".join(selected)

    custom_block = ""
    if custom_requirement and custom_requirement.strip():
        custom_block = f"\n## 用户自定义要求（必须严格满足）：\n{custom_requirement.strip()}\n"

    return f"""你是一位拥有 10 年经验的卖方行业首席分析师，写作风格对标中信证券、华泰、招商等头部券商的行业深度报告。

请为「**{industry}**」行业撰写一份完整的行业深度研究报告（draft，仅供研究参考）。

## 写作风格
{style_hint}

## 必须包含的章节（按此顺序）
对应的"7步行业研究框架"，请覆盖以下重点维度：**{selected_text}**

## 报告结构（务必严格遵循）

# {industry}行业深度报告
## 国产化 × 景气周期 × XX——副标题自拟

> 报告类型：行业深度（draft，仅供研究参考，不构成投资建议）
> 完成日期：{datetime.now().strftime('%Y-%m')}
> 适用对象：A 股二级市场配置型投资者

## 执行摘要（TL;DR）
- 用一段话给出**核心判断**
- 列出 **2-4 条投资主线**（注明 α/β/事件驱动属性）
- 给出**建议配置框架**（核心/弹性/观察分层）
- 说明**最大风险**

---

# 第一部分：宏观环境
## 1.1 政策面（必须列出近 12 个月关键政策时间表）
## 1.2 流动性 / 利率环境

# 第二部分：行业景气度
## 2.1 周期定位
## 2.2 供需结构（按子赛道列表/数字）

# 第三部分：投资逻辑的反面——风险与证伪信号
（用表格列：主线 → 关键假设 → 证伪信号）

# 第四部分：标的图谱
## 4.1 核心层（高确定性）
## 4.2 弹性层（高 β）
## 4.3 观察层（位置低、待催化）
（每只票需有：代码、名称、子赛道、投资逻辑、关键跟踪指标）

# 第五部分：估值横向对比
- 与全球同行对比
- 与自身历史对比（PE/PB 分位）

# 第六部分：行业跟踪表（评分卡）
（表格：维度 / 关键指标 / 数据源 / 当前状态 / ⭐评分），最后给综合评分

# 第七部分：催化剂日历（未来 6 个月）
（表格：时间 / 事件 / 影响标的 / 方向）

# 第八部分：研究节奏建议
分"每天/每周/每月/每季度"四档

# 附录 A：数据源清单
# 附录 B：报告局限性声明

## 硬性要求
1. 所有标题/章节都要保留，不可省略
2. 表格使用标准 Markdown 表格语法
3. 标的图谱至少给出 8 只 A 股代码（6 位数字）
4. 估值数据如不确定，请明确标注"估算"或"截至 XX 时点"
5. 全文 ≥ 3000 字
6. 末尾必须有免责声明，明确"不构成投资建议"
7. 数据如属推测，必须明确写"估算"二字，不要伪造精确数字
{custom_block}
现在开始撰写报告："""


# ---------- Kimi 流式调用 ----------

def stream_report(
    industry: str,
    style: str = "data_driven",
    custom_requirement: Optional[str] = None,
    focus_dims: Optional[List[str]] = None,
    temperature: float = 0.6,
) -> Generator[Dict[str, Any], None, None]:
    """
    流式生成行业报告。

    Yields:
        {"type": "meta", "industry": ..., "model": ...}
        {"type": "delta", "text": "..."}     ← 多次
        {"type": "done", "id": ..., "duration_ms": ..., "tokens": ...}
        {"type": "error", "message": ...}
    """
    if not KIMI_API_KEY:
        yield {"type": "error", "message": "未配置 KIMI_API_KEY 环境变量"}
        return

    prompt = _build_prompt(industry, style, custom_requirement, focus_dims)
    started = datetime.now()
    yield {"type": "meta", "industry": industry, "model": KIMI_MODEL, "started_at": started.isoformat()}

    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": KIMI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": True,
    }

    full_text_parts: List[str] = []
    try:
        with requests.post(
            f"{KIMI_BASE}/chat/completions",
            headers=headers, json=payload, stream=True, timeout=180,
        ) as r:
            if r.status_code != 200:
                yield {"type": "error", "message": f"Kimi HTTP {r.status_code}: {r.text[:300]}"}
                return
            # 强制 UTF-8 解码，避免 requests 默认按 ISO-8859-1 解 SSE 字节流
            r.encoding = "utf-8"
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("data: "):
                    data_str = raw[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            full_text_parts.append(delta)
                            yield {"type": "delta", "text": delta}
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.RequestException as e:
        yield {"type": "error", "message": f"Kimi 请求异常: {e}"}
        return

    full_text = "".join(full_text_parts)
    duration_ms = int((datetime.now() - started).total_seconds() * 1000)

    # 落库
    rid: Optional[int] = None
    try:
        with _conn() as c:
            cur = c.execute(
                """INSERT INTO industry_report
                   (industry,style,custom_requirement,focus_dims_json,content,model,tokens,duration_ms,status,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    industry, style, custom_requirement,
                    json.dumps(focus_dims or [], ensure_ascii=False),
                    full_text, KIMI_MODEL, len(full_text), duration_ms,
                    "completed", datetime.now().isoformat(),
                ),
            )
            c.commit()
            rid = cur.lastrowid
    except Exception as e:
        print(f"[industry_report] save error: {e}")

    yield {
        "type": "done",
        "id": rid,
        "duration_ms": duration_ms,
        "chars": len(full_text),
    }


# ---------- CRUD ----------

def list_reports(limit: int = 50) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, industry, style, model, tokens, duration_ms, status, created_at "
            "FROM industry_report ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_report(rid: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM industry_report WHERE id=?", (rid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["focus_dims"] = json.loads(d.pop("focus_dims_json") or "[]")
    except json.JSONDecodeError:
        d["focus_dims"] = []
    return d


def delete_report(rid: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM industry_report WHERE id=?", (rid,))
        c.commit()
        return cur.rowcount > 0
