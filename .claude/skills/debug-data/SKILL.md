---
name: debug-data
description: 检查项目数据链路异常。用户说"X 的数据怎么不对""为什么这只票拉不到""缓存好像脏了"时触发。对齐 Anthropic /debug-model 思路：列出具体问题而非泛泛而谈。
---

# Debug Data Skill

## Philosophy
不输出 "数据看起来正常" 这种废话。要么列出具体问题，要么明确写"未发现异常"。

## Diagnostic checklist

按顺序执行，每项给出明确结论：

### 1. 服务可达性
- `curl http://localhost:8000/health` 是否 200？
- 如果不可达：检查是否在 `backend/` 目录跑了 uvicorn

### 2. Redis 状态
- `redis-cli ping` → PONG？
- 否则：缓存层禁用，所有请求都打源站，性能会差

### 3. 实时行情链路（腾讯接口）
- `GET /api/stocks/realtime/{code}` 返回什么？
- 检查项：
  - 返回 null → 代码错误 / 已退市 / 腾讯接口拒绝
  - timestamp 是否在 30 秒内
  - price 是否 = 0（停牌或接口异常）

### 4. 历史 K 线链路（baostock）
- `GET /api/stocks/history/{code}?period=1m`
- 检查项：
  - baostock 是否已 login（首次调用慢属正常）
  - 返回条数 < 5 → 触发 fallback 重新拉
  - SQLite `stock_history` 表里该 code 的最新日期是否过旧

### 5. 财报数据（东方财富）
- `GET /api/earnings/{code}` 是否 404？
- 如果 404 但实时行情正常：东方财富的 REPORT_DATE 接口可能改字段，看 services/earnings_service.py 的 URL

### 6. 缓存 vs 源站不一致
- 同一个 code 多次刷新，价格不变？→ Redis TTL 可能没生效
- `redis-cli KEYS 'realtime:*'` 看 TTL：应该 ≤ 30s

### 7. 数据库脏数据
- `sqlite3 backend/data/stocks.db "SELECT stock_code, MAX(trade_date), COUNT(*) FROM stock_history GROUP BY stock_code ORDER BY 2 LIMIT 10"`
- 异常信号：max(trade_date) 是周末/节假日 / count < 30

## Output template

```
# 数据链路诊断报告

## 1. 服务可达性：✅/❌
{具体证据}

## 2. Redis：✅/❌/⚠️
{具体证据}

## 3. 实时行情：…
## 4. 历史K线：…
## 5. 财报数据：…
## 6. 缓存一致性：…
## 7. 数据库脏数据：…

## 发现的问题（具体到 file:line 或 代码:接口）
1. …
2. …

## 建议修复动作
1. …
2. …
```

## Hard rules
- 每一项必须给"是/否/警告"中之一，不要"看起来还行"
- 发现问题必须指出具体接口或代码位置
- 不修复，只报告；修复需要用户授权
