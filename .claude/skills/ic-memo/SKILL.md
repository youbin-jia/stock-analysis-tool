---
name: ic-memo
description: 生成 IC 投决备忘录（草稿）。用户说"帮我写一份 X 的投决备忘录""把这只票的逻辑整理一下"时触发。
---

# Investment Committee Memo Skill

## Philosophy
对齐 Anthropic private-equity 的 `/ic-memo`。
个人投资者也需要"把买入逻辑写下来"，避免事后归因偏误。

## Workflow

1. 先用 `stock-snapshot` skill 收集事实数据
2. 与用户确认核心 thesis（投资逻辑），不要替他想
3. 写入数据库：`POST /api/thesis`，把这份备忘录持久化
4. 输出 markdown 文本，供用户存档

## Required user inputs
在落笔前必须问全：
1. **一句话 thesis**：为什么现在买？
2. **关键假设**（2-4 条）：必须可证伪
3. **持有周期**：6-12 个月？3 年？
4. **目标价 / 止损价**：可以基于 DCF 或可比
5. **可证伪触发条件**：什么情况下逻辑被打破

缺一项就反问，不要替他写。

## Output template

```
# IC Memo: {名称}（{代码}）— {一句话 thesis}（draft）

日期：{today}
作者：{user}
持有周期：{horizon}
状态：active

## 1. 投资逻辑（Thesis）
{用户原话}

## 2. 关键假设
1. {可证伪的假设 1}
2. {可证伪的假设 2}
3. …

## 3. 估值
- 当前价：{current_price}
- 目标价：{target_price}（隐含上涨 X%）
- 止损价：{stop_loss}（隐含下跌 X%）
- 估值方法：{DCF / Comps / 其他}
- 关键假设输入：{从 /api/valuation/dcf 的 assumptions 字段贴过来}

## 4. 财务画像
（贴 /api/earnings/{code} 的关键指标）

## 5. 同行业位置
（贴 /api/valuation/comps/{code} 的相对估值结论）

## 6. 风险点
- {/api/earnings 的 red_flags}
- {催化剂日历里值得注意的事件}
- {用户补充的风险}

## 7. 触发条件（可证伪）
- 加仓：{……}
- 减仓 / 平仓：{……}
- **逻辑证伪信号**（必填）：{若 X 发生，承认错误并平仓}

## 8. 监测节奏
- 每周：{……}
- 每季度（财报后）：复核第 2 节关键假设

---
*本备忘录为个人研究草稿（draft），不构成投资建议。所有决策请基于自身风险承受能力。*
```

## Hard rules
- 第 7 节"逻辑证伪信号" 必填，不能跳过
- 标题必须含 `(draft)`
- 不要替用户编 thesis 内容，逐项确认
- 写完后调 `POST /api/thesis` 落库
