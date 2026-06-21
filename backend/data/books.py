"""
经典投资书籍数据库
所有内容均为对公开思想/方法论的原创总结，不包含书中原文摘录。
"""

BOOKS = [
    {
        "id": "intelligent-investor",
        "title": "聪明的投资者",
        "title_en": "The Intelligent Investor",
        "author": "本杰明·格雷厄姆",
        "year": 1949,
        "school": "价值投资",
        "tags": ["价值投资", "安全边际", "防御型投资", "市场先生"],
        "rating": 5,
        "summary": "价值投资的奠基之作。格雷厄姆将投资者分为防御型和进取型，强调以低于内在价值的价格买入股票，并以\"安全边际\"作为核心保护。书中提出\"市场先生\"寓言，告诫投资者应利用市场情绪而非被其驱使。",
        "core_principles": [
            {
                "title": "安全边际原则",
                "content": "买入价格必须显著低于内在价值，预留足够缓冲应对估值误差和不可预见风险。一般要求至少 30%-50% 的折扣。",
                "actionable": "买入前估算内在价值，要求当前价 ≤ 内在价值 × 0.7"
            },
            {
                "title": "市场先生隐喻",
                "content": "把市场视为情绪化的合伙人，每天报价但你可以选择是否交易。市场短期是投票机，长期是称重机。",
                "actionable": "避免追涨杀跌，在市场极度悲观时贪婪，极度乐观时谨慎"
            },
            {
                "title": "区分投资与投机",
                "content": "投资需保证本金安全并获得满意回报，否则即投机。基于事实分析的才叫投资。",
                "actionable": "每笔交易前问自己：是否基于企业基本面而非价格波动？"
            },
            {
                "title": "防御型投资策略",
                "content": "对大多数人推荐的策略：50%股票 + 50%债券，定期再平衡，只买大盘蓝筹和指数基金。",
                "actionable": "组合股债比例在 25%-75% 之间动态调整，每年再平衡一次"
            },
            {
                "title": "财务稳健筛选",
                "content": "选股的定量标准：流动比率>2，长期负债<营运资本，过去10年盈利稳定，连续20年分红，PE<15，PB<1.5。",
                "actionable": "可作为价值股初筛规则，PE×PB<22.5（格雷厄姆数）"
            }
        ],
        "quant_rules": [
            {"name": "格雷厄姆数", "formula": "PE × PB < 22.5", "use_case": "价值股筛选"},
            {"name": "安全边际", "formula": "(内在价值 - 当前价) / 内在价值 > 30%", "use_case": "买入决策"},
            {"name": "财务稳健", "formula": "流动比率>2 且 长期负债<营运资本", "use_case": "财务健康度"}
        ]
    },
    {
        "id": "security-analysis",
        "title": "证券分析",
        "title_en": "Security Analysis",
        "author": "本杰明·格雷厄姆 & 戴维·多德",
        "year": 1934,
        "school": "价值投资",
        "tags": ["证券分析", "财务分析", "估值", "学术"],
        "rating": 5,
        "summary": "价值投资学派的圣经，系统化建立了证券分析框架。强调通过深入研究财务报表、行业地位和管理层来评估证券真实价值，是定量分析的开创性著作。",
        "core_principles": [
            {
                "title": "定量优先于定性",
                "content": "数字可验证、可比较，定性判断易受偏见影响。分析应以财务数据为基础，定性因素作为补充。",
                "actionable": "建立标准化的财务指标对比表，横向行业对比 + 纵向历史对比"
            },
            {
                "title": "盈利能力的持续性",
                "content": "单年盈利不可靠，应取 7-10 年平均盈利来平滑周期影响。",
                "actionable": "使用 10 年平均 EPS 计算 Shiller PE (CAPE)"
            },
            {
                "title": "资产负债表分析",
                "content": "净流动资产 = 流动资产 - 总负债。当股价低于净流动资产的 2/3 时，是经典的\"烟蒂股\"机会。",
                "actionable": "筛选 P / NCAV < 0.67 的标的（适用于小盘股）"
            },
            {
                "title": "区分投资级与投机级证券",
                "content": "债券和优先股要看保护性条款；普通股看盈利能力。不同类型证券使用不同分析框架。",
                "actionable": "按证券类型应用不同估值方法，不混用"
            }
        ],
        "quant_rules": [
            {"name": "净流动资产法", "formula": "市值 < (流动资产 - 总负债) × 2/3", "use_case": "深度价值股"},
            {"name": "Shiller PE", "formula": "市值 / 10年平均通胀调整后EPS", "use_case": "市场整体估值"}
        ]
    },
    {
        "id": "one-up-wall-street",
        "title": "彼得林奇的成功投资",
        "title_en": "One Up On Wall Street",
        "author": "彼得·林奇",
        "year": 1989,
        "school": "成长投资",
        "tags": ["成长股", "GARP", "PEG", "散户优势"],
        "rating": 5,
        "summary": "林奇以麦哲伦基金13年29%年化收益率著称。他主张普通人通过观察日常生活就能发现优秀公司，并提出 PEG 估值法和六类公司分类法。",
        "core_principles": [
            {
                "title": "投资你了解的公司",
                "content": "从生活经验中发现公司：你购物的商场、使用的产品、孩子喜欢的品牌。在专业投资者关注前发现机会。",
                "actionable": "建立\"生活观察清单\"，记录注意到的优秀产品和服务"
            },
            {
                "title": "六类公司分类",
                "content": "缓慢增长型、稳定增长型、快速增长型、周期型、困境反转型、隐蔽资产型。每类对应不同投资逻辑。",
                "actionable": "买入前先归类，再用对应方法估值"
            },
            {
                "title": "PEG 估值法",
                "content": "PEG = PE / 盈利增长率。PEG < 1 通常意味着低估，PEG > 2 通常高估。",
                "actionable": "对成长股使用 PEG < 1 作为初筛条件"
            },
            {
                "title": "十倍股特征",
                "content": "名字平淡、业务无聊、被机构忽视、有重复消费、内部人在买入、回购股份、负债低。",
                "actionable": "用这些特征做反向筛选，关注小盘冷门优质股"
            },
            {
                "title": "持有逻辑变化才卖出",
                "content": "不因股价上涨而卖出，只在基本面恶化或买入逻辑被证伪时卖出。",
                "actionable": "建立买入论点清单，定期复核，论点不变就持有"
            }
        ],
        "quant_rules": [
            {"name": "PEG估值", "formula": "PEG = PE / EPS增长率(%) < 1", "use_case": "成长股估值"},
            {"name": "成长性筛选", "formula": "近3年净利润复合增速 > 20% 且 ROE > 15%", "use_case": "快速增长型公司"}
        ]
    },
    {
        "id": "buffett-letters",
        "title": "巴菲特致股东的信",
        "title_en": "Berkshire Hathaway Shareholder Letters",
        "author": "沃伦·巴菲特",
        "year": 1965,
        "school": "价值投资",
        "tags": ["长期投资", "护城河", "复利", "管理层"],
        "rating": 5,
        "summary": "巴菲特每年给伯克希尔股东的信，记录了他从格雷厄姆式\"烟蒂投资\"到费雪式\"优秀公司\"的转变。核心是用合理价格买入伟大公司并长期持有。",
        "core_principles": [
            {
                "title": "经济护城河",
                "content": "持久的竞争优势：品牌（可口可乐）、转换成本（微软）、网络效应（信用卡）、成本优势（GEICO）、特许经营权。",
                "actionable": "评估 ROE 长期>15% 且 ROIC > WACC 的公司，并分析其优势可持续性"
            },
            {
                "title": "能力圈原则",
                "content": "只投资能理解的生意。能力圈的大小不重要，知道边界在哪才重要。",
                "actionable": "为每笔投资写一份业务模式解释，能讲清楚再买"
            },
            {
                "title": "合理价格买伟大公司",
                "content": "用合理价格买伟大公司，远胜于用便宜价格买平庸公司。质量优先于价格折扣。",
                "actionable": "在 ROE>20%、毛利率稳定、低负债的公司中寻找估值合理标的"
            },
            {
                "title": "复利与长期持有",
                "content": "时间是好公司的朋友，平庸公司的敌人。频繁交易摧毁复利。最佳持有期是\"永远\"。",
                "actionable": "买入前问：若市场关闭5年我还愿意持有吗？"
            },
            {
                "title": "管理层品质",
                "content": "三项考察：诚实（如实披露）、能干（资本配置）、对股东负责（不滥发股票/期权）。",
                "actionable": "阅读过去10年年报，对比承诺与实际"
            },
            {
                "title": "别人贪婪我恐惧",
                "content": "市场情绪与机会成反比。在普遍乐观时谨慎，在普遍恐惧时进取。",
                "actionable": "用恐惧贪婪指数辅助判断市场情绪极端"
            }
        ],
        "quant_rules": [
            {"name": "高质量公司", "formula": "ROE(10年平均) > 15% 且 资产负债率 < 50%", "use_case": "护城河公司筛选"},
            {"name": "盈利质量", "formula": "经营现金流 / 净利润 > 1 (持续多年)", "use_case": "判断盈利真实性"}
        ]
    },
    {
        "id": "most-important-thing",
        "title": "投资最重要的事",
        "title_en": "The Most Important Thing",
        "author": "霍华德·马克斯",
        "year": 2011,
        "school": "价值投资 / 风险管理",
        "tags": ["风险管理", "周期", "二阶思维", "逆向投资"],
        "rating": 5,
        "summary": "橡树资本创始人马克斯的智慧总结。强调投资中风险控制比追求收益更重要，理解市场周期和二阶思维是超额收益的来源。",
        "core_principles": [
            {
                "title": "二阶思维",
                "content": "一阶思维：这是好公司，买入。二阶思维：这是好公司但所有人都知道因此已经高估，不买。要思考别人的思考。",
                "actionable": "决策前问：市场共识是什么？我的判断在多大程度上与共识不同？"
            },
            {
                "title": "理解市场周期",
                "content": "市场总在乐观与悲观间钟摆。在悲观底部买入，在乐观顶部卖出。极端情绪不可持续。",
                "actionable": "跟踪估值百分位（PE、PB历史分位），<20%加仓，>80%减仓"
            },
            {
                "title": "风险是永久损失本金的概率",
                "content": "学界用波动率衡量风险是错的。真实风险是基本面恶化或买价过高导致的永久损失。",
                "actionable": "评估下行情景：最坏情况下我损失多少？能否承受？"
            },
            {
                "title": "防御性投资",
                "content": "避免输家比寻找赢家更重要。好的投资者通过减少错误而非追求本垒打获胜。",
                "actionable": "组合中限制单一仓位（建议<10%），分散行业和风格"
            },
            {
                "title": "逆向投资但不盲目逆向",
                "content": "便宜本身不是买入理由，要分析为何便宜。逆向需要勇气，更需要正确的判断。",
                "actionable": "在情绪极端时，结合基本面判断是否真便宜还是价值陷阱"
            }
        ],
        "quant_rules": [
            {"name": "估值百分位", "formula": "当前PE在过去10年百分位 < 20%", "use_case": "周期底部识别"},
            {"name": "下行风险", "formula": "假设PE回归历史均值，潜在跌幅 < 20%", "use_case": "风险评估"}
        ]
    },
    {
        "id": "random-walk",
        "title": "漫步华尔街",
        "title_en": "A Random Walk Down Wall Street",
        "author": "伯顿·马尔基尔",
        "year": 1973,
        "school": "有效市场 / 被动投资",
        "tags": ["指数基金", "有效市场", "随机游走", "资产配置"],
        "rating": 4,
        "summary": "现代投资经典，论证短期股价近似随机游走，主动选股长期难以战胜指数。强烈推荐普通投资者通过指数基金和资产配置实现财富积累。",
        "core_principles": [
            {
                "title": "有效市场假说",
                "content": "公开信息已反映在股价中，依赖公开信息选股难以获得超额收益。",
                "actionable": "普通投资者放弃选股，定投宽基指数（沪深300、标普500）"
            },
            {
                "title": "成本是最大敌人",
                "content": "管理费、交易费、税收每年侵蚀收益。1%的费率差异在30年累计可达30%以上差距。",
                "actionable": "选择费率<0.5%的指数基金或 ETF"
            },
            {
                "title": "定期定投平滑成本",
                "content": "无需择时，定期投入固定金额能自动在低价时买入更多份额（平均成本法）。",
                "actionable": "每月固定日期定投，金额根据收入设定"
            },
            {
                "title": "生命周期资产配置",
                "content": "股票比例 ≈ (100 - 年龄)%，年轻时偏股，年长时偏债。",
                "actionable": "30岁: 70%股 / 50岁: 50%股 / 70岁: 30%股"
            },
            {
                "title": "多元化降低风险",
                "content": "跨资产、跨地区、跨行业的分散能降低非系统风险而不显著降低收益。",
                "actionable": "至少配置：国内股+海外股+债券+REITs+黄金"
            }
        ],
        "quant_rules": [
            {"name": "费率筛选", "formula": "指数基金综合费率 < 0.5%/年", "use_case": "基金选择"},
            {"name": "股债配比", "formula": "股票占比 = (110 - 年龄) %", "use_case": "资产配置"}
        ]
    },
    {
        "id": "reminiscences",
        "title": "股票作手回忆录",
        "title_en": "Reminiscences of a Stock Operator",
        "author": "埃德温·勒菲弗（基于杰西·利弗莫尔）",
        "year": 1923,
        "school": "技术分析 / 投机",
        "tags": ["趋势交易", "投机心理", "止损", "纪律"],
        "rating": 5,
        "summary": "记录了20世纪初传奇投机大师利弗莫尔的交易经验。虽是投机录，但其关于市场心理、纪律和风险管理的洞见至今适用于所有投资者。",
        "core_principles": [
            {
                "title": "顺势而为",
                "content": "不要与市场主趋势对抗。上升趋势中只做多，下降趋势中观望或做空。",
                "actionable": "用 200 日均线判断主趋势，价格在 MA200 之上做多"
            },
            {
                "title": "及时止损",
                "content": "判断错误时立刻认错，损失不超过本金的 10%。小亏损是交易成本，大亏损是灾难。",
                "actionable": "买入同时设止损位，损失 7%-10% 强制离场"
            },
            {
                "title": "让利润奔跑",
                "content": "盈利仓位不轻易兑现。截断亏损，让盈利奔跑（cut losses, let profits run）。",
                "actionable": "使用移动止损（如跌破 20 日均线），而非固定止盈位"
            },
            {
                "title": "等待最佳时机",
                "content": "钱不是在交易中赚到的，是在等待中赚到的。多数时间应保持观望。",
                "actionable": "每年只做几笔高确信度交易，避免过度交易"
            },
            {
                "title": "心理是最大敌人",
                "content": "贪婪、恐惧、希望、傲慢是交易者四大敌人。系统化交易能克服情绪。",
                "actionable": "写交易日记，复盘情绪化决策"
            }
        ],
        "quant_rules": [
            {"name": "趋势确认", "formula": "价格 > MA200 且 MA50 > MA200", "use_case": "多头趋势识别"},
            {"name": "止损规则", "formula": "亏损 ≥ 入场价 × 8% 强制平仓", "use_case": "风险控制"}
        ]
    },
    {
        "id": "irrational-exuberance",
        "title": "非理性繁荣",
        "title_en": "Irrational Exuberance",
        "author": "罗伯特·席勒",
        "year": 2000,
        "school": "行为金融",
        "tags": ["泡沫", "行为金融", "CAPE", "市场情绪"],
        "rating": 5,
        "summary": "诺贝尔奖得主席勒分析了股市和房市泡沫的成因。提出 CAPE（周期调整市盈率）指标，揭示了反馈循环、媒体放大、羊群效应等非理性行为如何推动资产泡沫。",
        "core_principles": [
            {
                "title": "CAPE 周期调整市盈率",
                "content": "用过去10年通胀调整后的平均盈利计算的 PE，能穿透短期波动反映长期估值水平。",
                "actionable": "CAPE > 25 警惕泡沫，> 30 高度警惕，< 15 长期机会"
            },
            {
                "title": "反馈循环理论",
                "content": "价格上涨→吸引更多买家→进一步推高价格→媒体报道→更多人入场。直至最后一个买家。",
                "actionable": "当媒体大肆报道、出租车司机谈股票时，警惕泡沫顶部"
            },
            {
                "title": "锚定与可得性偏差",
                "content": "人们用最近的高点作为参考点（锚定），过度依赖容易获得的信息（可得性）做决策。",
                "actionable": "估值时用基本面（盈利、现金流）而非历史价格作锚"
            },
            {
                "title": "群体过度自信",
                "content": "牛市后期，散户普遍认为自己能跑赢市场。群体信心达到峰值往往是反转信号。",
                "actionable": "关注开户数、融资余额等情绪指标极端值"
            }
        ],
        "quant_rules": [
            {"name": "CAPE估值", "formula": "Shiller PE > 历史90分位 视为高估", "use_case": "市场顶部识别"},
            {"name": "情绪指标", "formula": "融资余额/流通市值 处于历史极端", "use_case": "市场情绪监测"}
        ]
    },
    {
        "id": "common-stocks",
        "title": "怎样选择成长股",
        "title_en": "Common Stocks and Uncommon Profits",
        "author": "菲利普·费雪",
        "year": 1958,
        "school": "成长投资",
        "tags": ["成长股", "定性分析", "闲聊法", "长期持有"],
        "rating": 5,
        "summary": "成长投资学派创始人费雪的代表作。提出\"闲聊法\"调研，关注公司管理层、研发能力和长期增长潜力，对巴菲特影响深远（巴菲特说自己15%格雷厄姆+85%费雪）。",
        "core_principles": [
            {
                "title": "十五要点选股",
                "content": "包含产品潜力、研发投入、销售组织、利润率、管理层诚信等15个定性维度，重点考察长期增长能力。",
                "actionable": "建立公司评分卡，按15要点逐项打分"
            },
            {
                "title": "闲聊法（Scuttlebutt）",
                "content": "通过与公司客户、供应商、竞争对手、前员工交流，获取财报之外的信息。",
                "actionable": "调研产业链上下游、阅读招聘信息、消费者评论"
            },
            {
                "title": "管理层是关键",
                "content": "优秀管理层具有：长远眼光、对员工坦诚、研发投入、应对危机能力。",
                "actionable": "阅读历任CEO的发言和决策记录，评估言行一致性"
            },
            {
                "title": "极少卖出",
                "content": "正确买入后基本无需卖出。除非：判断错了、基本面变了、有显著更好的机会。",
                "actionable": "买入前严格筛选，买入后长期持有（10年+）"
            },
            {
                "title": "集中投资",
                "content": "深入研究少数公司远胜于浅尝多家。10-12 只精选股票即可。",
                "actionable": "组合控制在 10-15 只，每只仓位 5%-15%"
            }
        ],
        "quant_rules": [
            {"name": "研发强度", "formula": "研发费用 / 营收 > 行业均值", "use_case": "成长公司筛选"},
            {"name": "持续高成长", "formula": "近5年营收+利润复合增速 > 15%", "use_case": "成长股核心标准"}
        ]
    },
    {
        "id": "little-book-common-sense",
        "title": "约翰博格的常识投资",
        "title_en": "The Little Book of Common Sense Investing",
        "author": "约翰·博格",
        "year": 2007,
        "school": "被动投资",
        "tags": ["指数投资", "低成本", "长期持有", "ETF"],
        "rating": 5,
        "summary": "先锋基金创始人、指数基金之父博格的总结。用数据论证主动管理基金长期跑输指数，倡导低成本指数基金作为多数人的最优选择。",
        "core_principles": [
            {
                "title": "成本是确定的，收益是不确定的",
                "content": "市场长期年化约 7%，扣除 2% 主动基金费率后只剩 5%。复利下，成本差异决定退休时财富差异。",
                "actionable": "选择费率 < 0.2% 的宽基指数基金"
            },
            {
                "title": "回归均值",
                "content": "今年表现最好的基金，未来几年很可能跑输。短期排名靠前的基金不要追。",
                "actionable": "不追逐过去3年涨幅最高的基金，按规则定投宽基"
            },
            {
                "title": "买入并持有",
                "content": "频繁交易摧毁收益。每年换手率应低于 10%。",
                "actionable": "设定再平衡规则（如年度），平时不操作"
            },
            {
                "title": "拥有整个市场",
                "content": "购买全市场指数基金，免去选股选时压力，分享经济整体增长。",
                "actionable": "核心仓位配置沪深300+中证500（或全市场ETF）"
            }
        ],
        "quant_rules": [
            {"name": "低成本指数", "formula": "指数基金总费率 < 0.3%/年", "use_case": "基金筛选"},
            {"name": "组合换手率", "formula": "年度换手率 < 20%", "use_case": "纪律执行"}
        ]
    }
]


def get_all_books():
    """获取所有书籍简要信息"""
    return [
        {
            "id": b["id"],
            "title": b["title"],
            "title_en": b["title_en"],
            "author": b["author"],
            "year": b["year"],
            "school": b["school"],
            "tags": b["tags"],
            "rating": b["rating"],
            "summary": b["summary"],
            "principle_count": len(b["core_principles"]),
            "quant_rule_count": len(b["quant_rules"]),
        }
        for b in BOOKS
    ]


def get_book_by_id(book_id: str):
    """根据 ID 获取书籍详情"""
    for b in BOOKS:
        if b["id"] == book_id:
            return b
    return None


def get_all_schools():
    """获取所有流派"""
    return sorted(set(b["school"] for b in BOOKS))


def get_all_tags():
    """获取所有标签及计数"""
    from collections import Counter
    tag_counter = Counter()
    for b in BOOKS:
        tag_counter.update(b["tags"])
    return [{"tag": t, "count": c} for t, c in tag_counter.most_common()]


def get_all_principles():
    """获取所有核心经验（用于统一展示/搜索）"""
    result = []
    for b in BOOKS:
        for p in b["core_principles"]:
            result.append({
                "book_id": b["id"],
                "book_title": b["title"],
                "author": b["author"],
                "school": b["school"],
                "title": p["title"],
                "content": p["content"],
                "actionable": p["actionable"],
            })
    return result


def get_all_quant_rules():
    """获取所有可量化规则"""
    result = []
    for b in BOOKS:
        for r in b["quant_rules"]:
            result.append({
                "book_id": b["id"],
                "book_title": b["title"],
                "author": b["author"],
                "name": r["name"],
                "formula": r["formula"],
                "use_case": r["use_case"],
            })
    return result
