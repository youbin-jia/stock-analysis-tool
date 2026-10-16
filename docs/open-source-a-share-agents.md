# 可用于 A 股的开源炒股、投研与量化交易 Agent 调研

> 调研日期：2026-09-18  
> 信息范围：仅使用项目官方 GitHub、官方文档和论文。维护状态以调研日看到的默认分支最近提交或仓库更新时间为准。  
> 说明：这里的“可用于 A 股”分为三档：原生理解 A 股制度和特色数据、仅能读取 A 股行情、需要自行接入 A 股数据或券商。

## 结论先行

没有一个开源项目同时在以下四方面都足够成熟：可靠的 A 股数据、可复现的 Agent 决策、严格无未来函数的回测、经过验证的券商实盘执行。因此，不建议把任何项目直接用于无人值守实盘。

综合推荐顺序如下：

1. **TradingAgents-Astock**：当前最适合直接做 A 股多 Agent 个股投研，A 股制度和特色数据适配最深入，但不是完整量化回测或实盘系统。
2. **Microsoft RD-Agent + Qlib**：最适合因子挖掘、模型演化和组合回测，研究方法最完整；工程门槛高，不负责券商实盘。
3. **Vibe-Trading**：最完整的“研究 Agent + 策略生成 + A 股规则回测”工作台，活跃度很高；功能面很大，A 股实盘通道仍需自行核验和接入。
4. **QuantMind OSS**：功能最接近数据、因子、模型、回测、模拟盘、MiniQMT 实盘一体化；项目较新、系统复杂，实盘前必须审计代码和交易风控。
5. **TradingAgents-CN**：中文界面和 A 股多数据源较完善，适合本地部署体验；没有真实实盘，且采用混合许可证。
6. **TradingAgents 原版**：框架和论文影响力最大，现已接受 `.SS/.SZ` A 股代码并提供历史决策评估；A 股数据深度仍明显弱于专门分支。
7. **daily_stock_analysis**：适合每日自选股分析、报告和消息推送，部署简单；更像自动化投研助手，不是交易执行 Agent。
8. **Qbot**：覆盖面广，适合参考传统量化系统结构；公开版与专业版能力边界、许可证表述和工程成熟度存在问题，不建议作为新项目首选。

如果目标是本仓库后续集成，优先组合是：**TradingAgents-Astock 的多 Agent 工作流 + Qlib 的研究回测内核 + 独立、受风控约束的 MiniQMT/vn.py 执行层**。

## 核心对比

| 项目 | 定位 | A 股支持 | 数据源 | 回测 | 实盘 | 许可证 | 维护判断 |
|---|---|---|---|---|---|---|---|
| [TradingAgents-Astock](https://github.com/simonlin1212/TradingAgents-astock) | A 股特化多 Agent 投研 | **原生**：T+1、涨跌停、100 股、ST、沪深 300 基准；含政策、游资、解禁角色 | mootdx、腾讯、东方财富、新浪、同花顺、财联社、百度 | **有限**：主要是历史决策表现追踪，README 明确说明不等同策略回测 | **无**：只输出方向、评级和理由，不输出仓位、目标价或可执行订单 | Apache-2.0 | 活跃；默认分支 2026-09-16 仍有更新 |
| [RD-Agent](https://github.com/microsoft/RD-Agent) + [Qlib](https://github.com/microsoft/qlib) | 自动因子/模型研发与量化研究平台 | **原生研究支持**：Qlib 有 `REG_CN`、A 股数据格式和中国市场示例 | Qlib 数据集、自建 Qlib 数据；官方示例数据主要来自 Yahoo，另有 Baostock 采集器 | **强**：训练、组合构建、回测、分析、订单执行模拟 | **无现成券商实盘闭环**；Qlib 的 online serving 不等同券商下单 | 两者均 MIT | 很活跃；2026-09-15、09-16 仍有提交 |
| [Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) | 通用交易研究 Agent、策略生成、验证和回测工作台 | **原生**：A 股行情链和 `ChinaAEngine`，模拟印花税、T+1、涨跌停、100 股手数 | 腾讯、mootdx、东方财富、BaoStock、AkShare、Tushare、本地数据等 | **强**：多市场引擎、基准比较、Monte Carlo、Bootstrap、Walk-Forward | 有多券商连接器和受约束的自动交易能力，但未从官方说明确认成熟的中国内地券商 A 股下单闭环 | MIT | 极活跃；2026-09-18 仍有更新 |
| [QuantMind OSS](https://github.com/qusong0627/QuantMind) | AI 原生全栈量化平台 | **原生**：A 股、港股、美股、期货等 | QuantDB、Parquet/DuckDB、Qlib 数据及舆情源 | **强**：Qlib 回测、费用/滑点/涨跌停模拟、因子演化 | **有**：仓库声明支持 MiniQMT、通达信联动、模拟与实盘模式 | AGPL-3.0 | 活跃但年轻；2026-04 创建，2026-09-18 仍有更新 |
| [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) | TradingAgents 中文增强版 | **原生**：A/港/美股，中文报告和 A 股数据适配 | Tushare、AkShare、BaoStock；美股另有 Finnhub、Alpha Vantage、Yahoo | 路线图仍写“探索策略回测”；已有模拟交易模块 | **无**：README 明确“不提供实盘交易指令” | **混合许可证**：核心 Apache-2.0，`app/` 与 `frontend/` 为专有许可 | 中等；默认分支最后推送为 2026-07-24 |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | 论文对应的多 Agent 金融交易框架 | **基础支持**：接受沪市 `.SS`、深市 `.SZ` | 主要依赖 Yahoo Finance；可选 Alpha Vantage、SEC EDGAR、FRED 等 | **有**：v0.5.0 支持按股票和日期网格评估历史决策 | **无真实券商执行**；Portfolio Manager 发送到 simulated exchange | Apache-2.0 | 很活跃；2026-09-18 仍有更新 |
| [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | 每日股票分析、Agent 问股和推送系统 | **原生**：A/港/美/日/韩/台股和 ETF | AkShare、BaoStock、YFinance；可选 Tushare 等 | Web 工作台带回测；另有 AlphaEvo 项目负责策略回测和演化 | **无**：定位是分析、持仓管理和推送 | MIT | 很活跃；2026-09-13 仍有更新 |
| [Qbot](https://github.com/UFund-Me/Qbot) | 传统量化投研、策略、回测和交易平台合集 | **原生**：有 A 股策略和回测示例 | 开源依赖包含 AkShare；README 还列出 Tushare、Qlib、vn.py 等 | **有**：Backtrader 策略和 A 股示例 | README 宣称支持券商/模拟/实盘，但完整闭环主要列在付费 `pro` 版，公开版不可视为开箱即用实盘系统 | 仓库 `LICENSE` 是 MIT，但 README 写 CC BY-NC-SA 4.0，存在冲突 | 活跃度偏低；默认分支最近提交为 2026-03-11 |

## 逐项判断

### 1. TradingAgents-Astock

这是当前最直接的 A 股投研 Agent 选择。它不是简单中文翻译，而是把原版 TradingAgents 的数据层、角色和交易规则替换为 A 股实现：

- 支持 T+1、涨跌停、100 股手数、ST 等约束。
- 增加政策分析师、游资追踪师和解禁监控师。
- 使用免费直连数据源，减少对单一 API Key 的依赖。
- 全仓库采用 Apache-2.0，商业集成边界比 TradingAgents-CN 清晰。

主要限制：

- 项目明确表示历史判断记录不是完整策略回测：持有窗口可能重叠，缺少仓位管理、交易成本和冲击成本。
- 不生成可执行仓位、止损、目标价或真实订单。
- 一次完整分析通常需要 30 至 50 次 LLM 调用，成本和延迟不可忽略。
- 免费网页数据源存在接口变化、限流和封禁风险。

来源：[README](https://github.com/simonlin1212/TradingAgents-astock/blob/main/README.md)、[A 股数据实现](https://github.com/simonlin1212/TradingAgents-astock/blob/main/tradingagents/dataflows/a_stock.py)、[LICENSE](https://github.com/simonlin1212/TradingAgents-astock/blob/main/LICENSE)。

### 2. Microsoft RD-Agent + Qlib

二者应视为一套系统：RD-Agent 负责提出、实现和迭代因子/模型，Qlib 负责数据、训练、组合、回测和实验管理。它更接近“自动量化研究员”，而不是聊天式荐股 Agent。

优势：

- 研究闭环最完整，适合自动因子挖掘、模型联合优化和严格实验。
- Qlib 原生包含中国市场区域、A 股数据格式、回测和订单执行模拟。
- RD-Agent-Quant 有官方论文和可复现实验入口。

主要限制：

- RD-Agent 官方只支持 Linux，多数场景依赖 Docker、LLM 和 embedding 服务。
- Qlib 官方样例数据曾因数据安全政策暂停，README 推荐社区数据包或自行采集；公开 Yahoo 数据质量不应直接用于生产。
- “online serving”是滚动预测和模型管理能力，不代表已经接入国内券商交易柜台。
- 自动生成因子代码必须经过数据泄漏、未来函数、停牌、涨跌停和幸存者偏差审计。

来源：[RD-Agent README](https://github.com/microsoft/RD-Agent/blob/main/README.md)、[量化场景文档](https://rdagent.readthedocs.io/en/latest/scens/quant_agent_fin.html)、[R&D-Agent-Quant 论文](https://arxiv.org/abs/2505.15155)、[Qlib README](https://github.com/microsoft/qlib/blob/main/README.md)、[Qlib 数据文档](https://qlib.readthedocs.io/en/latest/component/data.html)、[Qlib LICENSE](https://github.com/microsoft/qlib/blob/main/LICENSE)。

### 3. Vibe-Trading

Vibe-Trading 更像一个完整的 Agent 研究操作系统：自然语言研究、策略代码生成、多 Agent 团队、数据获取、回测、验证、报告、记忆和经纪商连接都放在同一工作区。

对 A 股最有价值的部分是：

- A 股数据自动降级链：腾讯、mootdx、东方财富、BaoStock、AkShare、Tushare、本地数据。
- 专用 `ChinaAEngine`，覆盖印花税、T+1、涨跌停和 100 股手数。
- 支持基准比较、Monte Carlo、Bootstrap、Walk-Forward 和本地点时数据。

主要限制：

- 项目功能面很大、更新很快，部署和升级的测试成本高。
- 官方确有多券商连接器和自动交易安全门，但现有资料不足以把它认定为成熟的中国内地 A 股实盘方案。
- Agent 自动生成策略并不等于策略有效，仍需固定数据快照和独立复核。

来源：[README](https://github.com/HKUDS/Vibe-Trading/blob/main/README.md)、[回测模块](https://github.com/HKUDS/Vibe-Trading/tree/main/src/backtest)、[LICENSE](https://github.com/HKUDS/Vibe-Trading/blob/main/LICENSE)。

### 4. QuantMind OSS

QuantMind 是本次候选中最接近“一体化交易平台”的项目，官方架构覆盖数据、300+ 特征、RD-Agent 因子演化、13 类模型、Qlib 回测、模拟撮合、MiniQMT 和通达信联动。

主要限制：

- 项目于 2026 年 4 月创建，虽然更新活跃，但生产历史短。
- 系统由多个服务、数据库、Qlib 数据和 Windows QMT Agent 组成，运维面明显大于其他项目。
- README 的“生产就绪”和实盘能力属于项目方声明；真实资金使用前仍应逐项验证撤单、重复报单、断线恢复、交易日历、权限隔离和最大损失保护。
- AGPL-3.0 对网络服务修改版的源码提供义务需要提前评估。

来源：[README](https://github.com/qusong0627/QuantMind/blob/master/README.md)、[QMT Agent](https://github.com/qusong0627/QuantMind/tree/master/tools/qmt_agent)、[架构文档](https://github.com/qusong0627/QuantMind/blob/master/docs/development/architecture.md)、[LICENSE](https://github.com/qusong0627/QuantMind/blob/master/LICENSE)。

### 5. TradingAgents-CN

该项目适合希望快速获得中文 Web UI、国产模型和 A 股多数据源的人。仓库中能看到 Tushare、AkShare、BaoStock 的 provider、同步服务和大量相关测试，也包含模拟交易模块。

主要限制：

- README 明确定位为学习和研究，不提供实盘交易指令。
- README 的回测仍在长期路线图中，不能把模拟交易等同于严格回测。
- 许可证不是纯 Apache-2.0：`app/` 和 `frontend/` 是专有组件，商业使用需另行授权。
- README 同时描述已开源 v1.1.0、待开源 v2.0 和内测 v3.0，使用者应以当前仓库实际代码为准。

来源：[README](https://github.com/hsliuping/TradingAgents-CN/blob/main/README.md)、[数据源目录](https://github.com/hsliuping/TradingAgents-CN/tree/main/tradingagents/dataflows/providers/china)、[LICENSE](https://github.com/hsliuping/TradingAgents-CN/blob/main/LICENSE)、[模拟交易设计](https://github.com/hsliuping/TradingAgents-CN/blob/main/docs/design/paper_trading_multi_market_design.md)。

### 6. TradingAgents 原版

原版拥有清晰的多角色架构、官方论文和最大的生态。当前版本已经支持 Yahoo Finance 覆盖的 A 股代码，并能按股票和日期网格回放决策、按区域基准计算 alpha。

主要限制：

- A 股支持主要是代码识别和 Yahoo 行情覆盖，不包含政策、龙虎榜、解禁、北向资金等本地特征。
- SEC EDGAR 的点时基本面只适用于美国申报公司，A 股会回退到其他数据源。
- 回测评估的是 Agent 决策，不是具有完整成交、资金和 A 股制度约束的组合回测。
- 订单发送到 simulated exchange，不是券商实盘。

来源：[README](https://github.com/TauricResearch/TradingAgents/blob/main/README.md)、[论文](https://arxiv.org/abs/2412.20138)、[数据源实现](https://github.com/TauricResearch/TradingAgents/tree/main/tradingagents/dataflows)、[LICENSE](https://github.com/TauricResearch/TradingAgents/blob/main/LICENSE)。

### 7. daily_stock_analysis

该项目适合个人自选股日更：自动抓取行情、新闻和基本面，由 LLM 生成决策仪表盘，再通过企业微信、飞书、Telegram、邮件等渠道推送。它还提供 Web 工作台、Agent 问股、持仓和回测入口。

主要限制：

- 核心价值是分析与推送，不是自主交易执行。
- 多 Agent 编排在官方 README 中仍标记为实验性。
- 免费数据源受限流、接口变化和网络波动影响；长期批量任务需要更稳定的数据服务。

来源：[README](https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/README.md)、[市场支持边界](https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/docs/market-support.md)、[完整指南](https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/docs/full-guide.md)、[LICENSE](https://github.com/ZhuLinsen/daily_stock_analysis/blob/main/LICENSE)。

### 8. Qbot

Qbot 把数据、策略、Backtrader 回测、vn.py、Qlib、模拟交易和交易接口放在一个大仓库中，A 股示例较多，适合学习传统量化平台如何组织。

主要限制：

- README 一处称免费开源版提供完整闭环，版本表又把 AI 选股、数据清洗、回测、模拟和实盘全流程放入付费 `pro` 版，能力边界不清楚。
- 根目录 `LICENSE` 是 MIT，但 README 的许可证章节写“署名-非商业性使用-相同方式共享 4.0”，法律表述冲突。
- README 自己承认框架较乱、策略抽象和数据实时性仍待完善。
- 公开仓库最近提交距调研日约半年，活跃度弱于其他主要候选。

来源：[README](https://github.com/UFund-Me/Qbot/blob/main/README.md)、[requirements.txt](https://github.com/UFund-Me/Qbot/blob/main/requirements.txt)、[交易模块](https://github.com/UFund-Me/Qbot/tree/main/pytrader)、[LICENSE](https://github.com/UFund-Me/Qbot/blob/main/LICENSE)。

## 可作为 Agent 数据工具的补充项目

[A-Share Data Quant](https://github.com/jangviktor-web/a-stock-data-quant) 不是自主决策 Agent，而是可被 Agent 调用的 A 股数据与量化技能。它提供 A/港股行情、技术指标、七类策略回测、资金流、F10、研报公告以及多数据源降级，许可证为 MIT-0。适合补足 Agent 的数据工具层，但没有订单执行和组合级实盘风控。

来源：[README](https://github.com/jangviktor-web/a-stock-data-quant/blob/master/README.md)、[SKILL.md](https://github.com/jangviktor-web/a-stock-data-quant/blob/master/SKILL.md)、[LICENSE](https://github.com/jangviktor-web/a-stock-data-quant/blob/master/LICENSE)。

## 选择建议

| 目标 | 首选 | 次选 | 原因 |
|---|---|---|---|
| A 股个股多 Agent 研究 | TradingAgents-Astock | TradingAgents-CN | 前者 A 股规则更深入且许可证更清晰；后者 UI 和数据管理更完整 |
| 因子挖掘、模型研究、组合回测 | RD-Agent + Qlib | QuantMind | 前者研究可信度和可复现性更强；后者集成度更高 |
| 自然语言生成策略并严格验证 | Vibe-Trading | RD-Agent + Qlib | 前者工作流完整，后者更适合专业量化实验 |
| 每日自选股报告和推送 | daily_stock_analysis | TradingAgents-Astock | 部署和自动化成本较低 |
| 尝试 MiniQMT 实盘集成 | QuantMind | 自建 Agent + 独立执行层 | QuantMind 已提供相关代码，但必须先做隔离环境和模拟盘验证 |
| 学习传统量化平台架构 | Qbot | Qlib | Qbot 示例面广，Qlib 的研究架构更规范 |

## 实盘前的最低验收线

无论选择哪个项目，接入真实资金前至少应满足：

1. 数据按当时可见时间截断，避免财报、新闻和复权数据产生未来函数。
2. 回测覆盖停牌、涨跌停、T+1、100 股整数手、印花税、佣金、滑点和退市证券。
3. Agent 输出经过确定性 schema 校验，模型不能直接构造任意券商请求。
4. 交易层具备单票、行业、组合、日内亏损和总敞口上限。
5. 下单接口实现幂等键、重复报单防护、成交回报核对、断线恢复和人工急停。
6. 先完成历史回测、走样本外、仿真盘和小资金灰度，不能用 README 示例收益替代验证。

## 不列入首选的项目

[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) 是成熟度较高的通用金融 Agent 平台，适合美股基本面研究、估值和报告生成，但官方开源数据栈主要是 FMP、Finnhub、Yahoo Finance 和 SEC EDGAR，没有原生 A 股数据、制度或内地券商执行支持，因此不列入 A 股首选。

来源：[FinRobot README](https://github.com/AI4Finance-Foundation/FinRobot/blob/master/README.md)、[官方论文](https://arxiv.org/abs/2405.14767)、[LICENSE](https://github.com/AI4Finance-Foundation/FinRobot/blob/master/LICENSE)。
