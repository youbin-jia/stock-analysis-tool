---
name: dcf-model
description: 引导式 DCF 估值。用户说"帮我做 DCF""估一下 X 的内在价值"时触发。所有假设必须由用户显式提供，禁止硬编码。
---

# DCF Model Skill

## Philosophy
对齐 Anthropic financial-analysis 仓库的 `/dcf` + `/debug-model` 精神：
- **所有假设显式传入**，不要从 prompt 里"猜"
- 强制做敏感性分析
- 终值占 EV 超过 70% 必须提醒

## Workflow

### Step 1: 收集假设（必须问全）
在调用接口前，确保用户提供：
1. **基期 FCF（亿元）**：最近一期自由现金流，用户必须确认口径（FCFF 还是 FCFE）
2. **显性预测期年增长率**：通常 5-10 年的逐年增长率序列
3. **永续增长率 g**：A 股大盘股一般 2%-3%，超过 5% 必质询
4. **WACC**：合理区间 8%-12%
5. **净债务（亿元）**：可为负（净现金）
6. **总股本（亿股）**

缺一项，就反问用户，不要默认。

### Step 2: 调接口
```
POST /api/valuation/dcf
{ fcf_base, growth_rates, terminal_growth, wacc, net_debt, shares_out }
```

### Step 3: 强制做敏感性
```
POST /api/valuation/dcf/sensitivity
```
即使用户没要求，也必须做。

### Step 4: Debug 检查（学 /debug-model）
对输出做下列检查并明确指出问题：
- [ ] terminal_pv / enterprise_value > 70%？→ 提醒"终值依赖过高"
- [ ] warnings 数组非空？→ 全部转述给用户
- [ ] growth_rates 最后一年 < terminal_growth？→ 警告"显性末期增速 ≤ 永续增速，不一致"
- [ ] 用户给的 fcf_base 是否与最近年报数据对齐？让用户口头确认

## Output template

```
# {标的} DCF 估值（draft）

## 假设回显
- 基期 FCF：{} 亿
- 显性期增长率：{}
- 永续增长 g：{}
- WACC：{}
- 净债务：{} 亿
- 股本：{} 亿股

## 估值结果
- 企业价值 EV：{} 亿
- 股权价值：{} 亿
- **每股内在价值：{} 元**
- 终值占 EV：{}%（{是否健康}）

## 敏感性表（每股内在价值）
（贴矩阵）

## Debug 报告
- ✅/⚠️ 各项检查结果

## 复核 checklist
- [ ] FCF 口径（FCFF/FCFE）一致
- [ ] WACC 拆解（无风险利率/β/股权风险溢价）来源可追溯
- [ ] 永续增长率与长期 GDP 增速可比
- [ ] 净债务取自最新资产负债表

---
免责声明：DCF 结果对假设极度敏感（draft），请配合敏感性表使用，不构成投资建议。
```
