---
name: stock-snapshot
description: 给定 A 股代码，生成"实时行情 + 技术面 + 财报 + 估值 + 事件"的综合一页快照（draft）。用户说"看一下 600519""帮我快照贵州茅台"时触发。
---

# Stock Snapshot Skill

## When to use
用户给一个 A 股股票代码（或一句话提到某只 A 股），需要 30 秒内有一个全景概览：当前价格、近期走势、最新财报、估值水平、近期事件。

## Workflow

### 1. 启动 backend
确认 `http://localhost:8000/health` 可达。如果不可达，提示用户在 `backend/` 目录跑 `python -m uvicorn main:app --reload --port 8000`。

### 2. 并行调用以下 5 个接口

| 维度 | 接口 |
|---|---|
| 实时行情 | `GET /api/stocks/realtime/{code}` |
| 历史K线（近 60 日） | `GET /api/stocks/history/{code}?period=3m` |
| 财报快评 | `GET /api/earnings/{code}` |
| 同行可比 | `GET /api/valuation/comps/{code}` |
| 个股事件 | `GET /api/calendar/stock/{code}?days=180` |

任何一项失败，不要让整个流程崩，标注"该项数据缺失"继续。

### 3. 计算技术面要点（基于历史K线）
- 距 60 日最高/最低的位置
- 5/20/60 日均线相对关系（多头/空头/纠缠）
- 最近 5 日成交量 vs 20 日均量

### 4. 输出固定结构

```
# {名称}（{代码}）一页快照（draft，{生成时间}）

## 一、价格与技术面
- 现价 / 涨跌幅 / 成交额
- 距 60 日高/低 X%
- 均线结构：……

## 二、最新财报（{报告期}）
- 营收 / 同比 / 净利 / 同比 / ROE
- 自动 red flags：……

## 三、相对估值
- 行业：{industry}
- PE(TTM) / PB / ROE vs 行业中位
- 一句话定性：偏贵 / 合理 / 偏便宜

## 四、未来 180 天事件
- 财报披露：…
- 解禁：…
- 分红：…

## 五、需人工复核的点（必写）
- 列出 2-4 项必须人工核实的内容（如：是否有非经常性损益、行业划分是否准确）

## 免责声明
本快照由系统基于公开数据自动生成（draft），仅供研究参考，不构成投资建议。
```

## Hard rules
- 永远在标题加 `(draft)`
- 永远在结尾加免责声明
- 数据缺失项标 `—`，不要编造
- 不要给"买入/卖出/持有"评级
