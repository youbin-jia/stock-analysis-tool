"""
基于经典投资书籍经验的多流派评分引擎

每个流派对应一组从书籍中提炼的可量化规则，对单只股票输出：
- 流派评分（0-100）
- 触发的规则清单（含书籍出处）
- 优势/劣势诊断
"""
from typing import Dict, Any, List


# ============================================================
# 流派规则定义 —— 直接对应 backend/data/books.py 中的 quant_rules
# ============================================================

STYLES = {
    "graham_deep_value": {
        "name": "格雷厄姆深度价值",
        "books": ["intelligent-investor", "security-analysis"],
        "description": "格雷厄姆经典价值投资法：低 PE+PB、低负债、足够安全边际。适合熊市与防御阶段。",
        "key_principle": "用 30%-50% 折扣买入有形资产支撑的便宜股票",
    },
    "buffett_quality": {
        "name": "巴菲特护城河质量",
        "books": ["buffett-letters", "common-stocks"],
        "description": "用合理价格买伟大公司：长期高 ROE、低负债、盈利可预测、估值合理。",
        "key_principle": "时间是好公司的朋友，平庸公司的敌人",
    },
    "lynch_growth": {
        "name": "林奇 / 费雪 成长",
        "books": ["one-up-wall-street", "common-stocks"],
        "description": "GARP 策略：成长与估值结合，PEG<1，业绩稳定增长。",
        "key_principle": "PEG < 1 是成长股的便宜信号",
    },
    "marks_defensive": {
        "name": "马克斯防御 / 周期",
        "books": ["most-important-thing", "irrational-exuberance"],
        "description": "风险优先：估值不极端、下行可控、避免周期顶部。",
        "key_principle": "避免输家比寻找赢家更重要",
    },
}


# ============================================================
# 规则评估器 —— 每条规则返回 (是否触发, 得分, 描述)
# ============================================================

def _grade(value, thresholds, descending=False):
    """根据阈值返回 (等级 0-1, 描述)。descending=True 表示值越小越好。"""
    if value is None:
        return 0.0, "无数据"
    levels = thresholds if not descending else list(reversed(thresholds))
    if descending:
        for i, t in enumerate(thresholds):
            if value <= t:
                return 1.0 - i * 0.25, f"≤{t}"
        return 0.0, f">{thresholds[-1]}"
    else:
        for i, t in enumerate(reversed(thresholds)):
            if value >= t:
                return 1.0 - i * 0.25, f"≥{t}"
        return 0.0, f"<{thresholds[0]}"


def _safe_pos(x):
    return x if x and x > 0 else None


# ============================================================
# 流派 1: 格雷厄姆深度价值
# ============================================================

def score_graham_deep_value(d: Dict[str, Any]) -> Dict[str, Any]:
    pe, pb = _safe_pos(d.get("pe_ttm")), _safe_pos(d.get("pb"))
    debt = d.get("debt_ratio")
    div = d.get("dividend_yield") or 0
    rules = []
    score = 0
    total_weight = 0

    # 规则 1: 格雷厄姆数 PE×PB < 22.5（权重 35）
    w = 35
    total_weight += w
    if pe and pb:
        graham_num = pe * pb
        if graham_num < 15:
            s, msg = 100, f"PE×PB={graham_num:.1f}，深度低估"
        elif graham_num < 22.5:
            s, msg = 80, f"PE×PB={graham_num:.1f}，符合格雷厄姆数"
        elif graham_num < 40:
            s, msg = 50, f"PE×PB={graham_num:.1f}，略高"
        else:
            s, msg = 15, f"PE×PB={graham_num:.1f}，明显高估"
        rules.append({
            "rule": "格雷厄姆数 PE×PB < 22.5",
            "book": "聪明的投资者",
            "passed": graham_num < 22.5,
            "value": round(graham_num, 1),
            "comment": msg,
        })
        score += s * w
    else:
        rules.append({"rule": "格雷厄姆数", "book": "聪明的投资者", "passed": False, "value": None, "comment": "缺少PE或PB"})

    # 规则 2: PE < 15（权重 20）
    w = 20
    total_weight += w
    if pe:
        passed = pe < 15
        s = 100 if pe < 10 else 75 if pe < 15 else 40 if pe < 25 else 10
        rules.append({
            "rule": "防御型投资 PE < 15",
            "book": "聪明的投资者",
            "passed": passed,
            "value": round(pe, 2),
            "comment": f"PE={pe:.2f}",
        })
        score += s * w

    # 规则 3: PB < 1.5（权重 15）
    w = 15
    total_weight += w
    if pb:
        passed = pb < 1.5
        s = 100 if pb < 1 else 75 if pb < 1.5 else 40 if pb < 2.5 else 10
        rules.append({
            "rule": "防御型投资 PB < 1.5",
            "book": "聪明的投资者",
            "passed": passed,
            "value": round(pb, 2),
            "comment": f"PB={pb:.2f}",
        })
        score += s * w

    # 规则 4: 财务稳健 资产负债率 < 50%（权重 20）
    w = 20
    total_weight += w
    if debt is not None:
        passed = debt < 0.5
        s = 100 if debt < 0.3 else 75 if debt < 0.5 else 40 if debt < 0.7 else 10
        rules.append({
            "rule": "财务稳健 资产负债率 < 50%",
            "book": "证券分析",
            "passed": passed,
            "value": round(debt * 100, 1),
            "comment": f"资产负债率={debt*100:.1f}%",
        })
        score += s * w

    # 规则 5: 持续分红（权重 10）
    w = 10
    total_weight += w
    passed = div > 1
    s = 100 if div > 3 else 70 if div > 1 else 30
    rules.append({
        "rule": "稳定派息 股息率 > 1%",
        "book": "聪明的投资者",
        "passed": passed,
        "value": round(div, 2),
        "comment": f"股息率={div:.2f}%" if div else "无股息数据",
    })
    score += s * w

    final = round(score / total_weight, 1) if total_weight else 0
    passed_count = sum(1 for r in rules if r["passed"])
    return {
        "style": "graham_deep_value",
        "score": final,
        "rules": rules,
        "passed_count": passed_count,
        "total_rules": len(rules),
    }


# ============================================================
# 流派 2: 巴菲特护城河质量
# ============================================================

def score_buffett_quality(d: Dict[str, Any]) -> Dict[str, Any]:
    roe = d.get("roe") or 0
    pe = _safe_pos(d.get("pe_ttm"))
    pb = _safe_pos(d.get("pb"))
    debt = d.get("debt_ratio")
    npm = d.get("net_profit_margin") or 0
    rules = []
    score = 0
    total_weight = 0

    # 规则 1: 高 ROE > 15%（权重 35）—— 护城河核心
    w = 35
    total_weight += w
    passed = roe > 0.15
    s = 100 if roe > 0.20 else 80 if roe > 0.15 else 50 if roe > 0.10 else 20
    rules.append({
        "rule": "高质量公司 ROE > 15%",
        "book": "巴菲特致股东的信",
        "passed": passed,
        "value": round(roe * 100, 2),
        "comment": f"ROE={roe*100:.2f}%",
    })
    score += s * w

    # 规则 2: 低负债 资产负债率 < 50%（权重 20）
    w = 20
    total_weight += w
    if debt is not None:
        passed = debt < 0.5
        s = 100 if debt < 0.3 else 75 if debt < 0.5 else 40 if debt < 0.7 else 10
        rules.append({
            "rule": "财务稳健 资产负债率 < 50%",
            "book": "巴菲特致股东的信",
            "passed": passed,
            "value": round(debt * 100, 1),
            "comment": f"资产负债率={debt*100:.1f}%",
        })
        score += s * w

    # 规则 3: 净利率反映定价权（权重 15）
    w = 15
    total_weight += w
    passed = npm > 0.10
    s = 100 if npm > 0.20 else 75 if npm > 0.10 else 40 if npm > 0.05 else 10
    rules.append({
        "rule": "盈利质量 净利率 > 10%",
        "book": "怎样选择成长股",
        "passed": passed,
        "value": round(npm * 100, 2),
        "comment": f"净利率={npm*100:.2f}%",
    })
    score += s * w

    # 规则 4: 合理价格 PE < 30（权重 20）—— 合理价格买伟大公司
    w = 20
    total_weight += w
    if pe:
        passed = pe < 30
        s = 100 if pe < 20 else 75 if pe < 30 else 40 if pe < 50 else 10
        rules.append({
            "rule": "合理价格 PE < 30",
            "book": "巴菲特致股东的信",
            "passed": passed,
            "value": round(pe, 2),
            "comment": f"PE={pe:.2f}",
        })
        score += s * w

    # 规则 5: PB 不极端（权重 10）
    w = 10
    total_weight += w
    if pb:
        passed = pb < 5
        s = 100 if pb < 3 else 70 if pb < 5 else 40 if pb < 8 else 10
        rules.append({
            "rule": "估值控制 PB < 5",
            "book": "巴菲特致股东的信",
            "passed": passed,
            "value": round(pb, 2),
            "comment": f"PB={pb:.2f}",
        })
        score += s * w

    final = round(score / total_weight, 1) if total_weight else 0
    passed_count = sum(1 for r in rules if r["passed"])
    return {
        "style": "buffett_quality",
        "score": final,
        "rules": rules,
        "passed_count": passed_count,
        "total_rules": len(rules),
    }


# ============================================================
# 流派 3: 林奇 / 费雪 成长
# ============================================================

def score_lynch_growth(d: Dict[str, Any]) -> Dict[str, Any]:
    pe = _safe_pos(d.get("pe_ttm"))
    rev_g = d.get("revenue_growth") or 0
    np_g = d.get("net_profit_growth") or 0
    roe = d.get("roe") or 0
    debt = d.get("debt_ratio")
    rules = []
    score = 0
    total_weight = 0

    # 规则 1: PEG < 1（权重 35）—— 林奇核心
    w = 35
    total_weight += w
    if pe and np_g > 0:
        peg = pe / (np_g * 100)
        passed = peg < 1
        s = 100 if peg < 0.5 else 80 if peg < 1 else 45 if peg < 2 else 10
        rules.append({
            "rule": "PEG 估值 PEG < 1",
            "book": "彼得林奇的成功投资",
            "passed": passed,
            "value": round(peg, 2),
            "comment": f"PEG={peg:.2f} (PE={pe:.1f}, 利润增速={np_g*100:.1f}%)",
        })
        score += s * w
    else:
        rules.append({
            "rule": "PEG 估值",
            "book": "彼得林奇的成功投资",
            "passed": False,
            "value": None,
            "comment": "缺少PE或正增速",
        })

    # 规则 2: 营收增速 > 15%（权重 20）
    w = 20
    total_weight += w
    passed = rev_g > 0.15
    s = 100 if rev_g > 0.30 else 80 if rev_g > 0.15 else 50 if rev_g > 0.05 else 10
    rules.append({
        "rule": "持续高成长 营收增速 > 15%",
        "book": "怎样选择成长股",
        "passed": passed,
        "value": round(rev_g * 100, 2),
        "comment": f"营收增速={rev_g*100:.2f}%",
    })
    score += s * w

    # 规则 3: 利润增速 > 20%（权重 20）—— 快速增长型
    w = 20
    total_weight += w
    passed = np_g > 0.20
    s = 100 if np_g > 0.30 else 80 if np_g > 0.20 else 50 if np_g > 0.10 else 10
    rules.append({
        "rule": "快速增长 净利润增速 > 20%",
        "book": "彼得林奇的成功投资",
        "passed": passed,
        "value": round(np_g * 100, 2),
        "comment": f"利润增速={np_g*100:.2f}%",
    })
    score += s * w

    # 规则 4: ROE > 15%（权重 15）
    w = 15
    total_weight += w
    passed = roe > 0.15
    s = 100 if roe > 0.20 else 75 if roe > 0.15 else 40 if roe > 0.10 else 10
    rules.append({
        "rule": "盈利能力 ROE > 15%",
        "book": "彼得林奇的成功投资",
        "passed": passed,
        "value": round(roe * 100, 2),
        "comment": f"ROE={roe*100:.2f}%",
    })
    score += s * w

    # 规则 5: 不靠杠杆 负债率 < 60%（权重 10）
    w = 10
    total_weight += w
    if debt is not None:
        passed = debt < 0.6
        s = 100 if debt < 0.4 else 70 if debt < 0.6 else 30
        rules.append({
            "rule": "低杠杆 资产负债率 < 60%",
            "book": "彼得林奇的成功投资",
            "passed": passed,
            "value": round(debt * 100, 1),
            "comment": f"资产负债率={debt*100:.1f}%",
        })
        score += s * w

    final = round(score / total_weight, 1) if total_weight else 0
    passed_count = sum(1 for r in rules if r["passed"])
    return {
        "style": "lynch_growth",
        "score": final,
        "rules": rules,
        "passed_count": passed_count,
        "total_rules": len(rules),
    }


# ============================================================
# 流派 4: 马克斯防御 / 周期
# ============================================================

def score_marks_defensive(d: Dict[str, Any]) -> Dict[str, Any]:
    pe = _safe_pos(d.get("pe_ttm"))
    pb = _safe_pos(d.get("pb"))
    debt = d.get("debt_ratio")
    div = d.get("dividend_yield") or 0
    roe = d.get("roe") or 0
    rules = []
    score = 0
    total_weight = 0

    # 规则 1: 估值不极端 PE < 25（权重 25）
    w = 25
    total_weight += w
    if pe:
        passed = pe < 25
        s = 100 if pe < 15 else 80 if pe < 25 else 40 if pe < 40 else 10
        rules.append({
            "rule": "估值不极端 PE < 25",
            "book": "投资最重要的事",
            "passed": passed,
            "value": round(pe, 2),
            "comment": f"PE={pe:.2f}",
        })
        score += s * w

    # 规则 2: 下行风险评估 PB < 3（权重 25）
    w = 25
    total_weight += w
    if pb:
        passed = pb < 3
        s = 100 if pb < 1.5 else 75 if pb < 3 else 35 if pb < 5 else 10
        rules.append({
            "rule": "下行风险可控 PB < 3",
            "book": "投资最重要的事",
            "passed": passed,
            "value": round(pb, 2),
            "comment": f"PB={pb:.2f}",
        })
        score += s * w

    # 规则 3: 防御性 高股息率 > 2%（权重 20）
    w = 20
    total_weight += w
    passed = div > 2
    s = 100 if div > 4 else 75 if div > 2 else 40 if div > 1 else 15
    rules.append({
        "rule": "防御性 股息率 > 2%",
        "book": "投资最重要的事",
        "passed": passed,
        "value": round(div, 2),
        "comment": f"股息率={div:.2f}%",
    })
    score += s * w

    # 规则 4: 避免高杠杆 资产负债率 < 60%（权重 20）
    w = 20
    total_weight += w
    if debt is not None:
        passed = debt < 0.6
        s = 100 if debt < 0.4 else 75 if debt < 0.6 else 30 if debt < 0.8 else 5
        rules.append({
            "rule": "避免高杠杆 资产负债率 < 60%",
            "book": "投资最重要的事",
            "passed": passed,
            "value": round(debt * 100, 1),
            "comment": f"资产负债率={debt*100:.1f}%",
        })
        score += s * w

    # 规则 5: 盈利稳定 ROE > 8%（权重 10）—— 二阶思维：不仅要便宜还要质量
    w = 10
    total_weight += w
    passed = roe > 0.08
    s = 100 if roe > 0.15 else 70 if roe > 0.08 else 30
    rules.append({
        "rule": "盈利稳定 ROE > 8%",
        "book": "投资最重要的事",
        "passed": passed,
        "value": round(roe * 100, 2),
        "comment": f"ROE={roe*100:.2f}% (避免价值陷阱)",
    })
    score += s * w

    final = round(score / total_weight, 1) if total_weight else 0
    passed_count = sum(1 for r in rules if r["passed"])
    return {
        "style": "marks_defensive",
        "score": final,
        "rules": rules,
        "passed_count": passed_count,
        "total_rules": len(rules),
    }


# ============================================================
# 入口：对一只股票输出全部流派评分
# ============================================================

STYLE_SCORERS = {
    "graham_deep_value": score_graham_deep_value,
    "buffett_quality": score_buffett_quality,
    "lynch_growth": score_lynch_growth,
    "marks_defensive": score_marks_defensive,
}


def score_all_styles(fundamental: Dict[str, Any]) -> Dict[str, Any]:
    """
    对一只股票输出 4 个流派的评分 + 综合评分 + 最佳流派标签。
    fundamental: 基本面数据（同 _fetch_stock_fundamental 返回结构）
    """
    style_results = {}
    for key, scorer in STYLE_SCORERS.items():
        style_results[key] = scorer(fundamental)

    # 最佳流派 = 得分最高
    best_key = max(style_results, key=lambda k: style_results[k]["score"])
    best = style_results[best_key]

    # 综合评分 = 4 流派平均
    composite = round(
        sum(r["score"] for r in style_results.values()) / len(style_results), 1
    )

    return {
        "composite_score": composite,
        "best_style": {
            "key": best_key,
            "name": STYLES[best_key]["name"],
            "score": best["score"],
            "key_principle": STYLES[best_key]["key_principle"],
        },
        "styles": [
            {
                "key": k,
                "name": STYLES[k]["name"],
                "description": STYLES[k]["description"],
                "books": STYLES[k]["books"],
                "key_principle": STYLES[k]["key_principle"],
                **style_results[k],
            }
            for k in STYLE_SCORERS.keys()
        ],
    }


def interpret_market_valuation(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    用席勒/马克斯的周期思想解读市场估值。
    market: {pe_ttm_median, pe_percentile, pb_median, pb_percentile, dividend_yield}
    """
    pe_pct = market.get("pe_percentile") or 0
    pb_pct = market.get("pb_percentile") or 0
    avg_pct = (pe_pct + pb_pct) / 2 if (pe_pct or pb_pct) else 0

    # 市场温度判断（基于估值百分位）
    if avg_pct < 20:
        temperature = "极冷"
        sentiment = "市场恐惧"
        suggestion = "马克斯：别人恐惧我贪婪。当前估值百分位极低，是长期布局窗口。"
        action = "积极加仓 / 定投提速"
        color = "blue"
    elif avg_pct < 40:
        temperature = "偏冷"
        sentiment = "悲观"
        suggestion = "估值低于历史 40% 分位，安全边际较好，可分批建仓。"
        action = "正常仓位 / 适度加仓"
        color = "cyan"
    elif avg_pct < 60:
        temperature = "温和"
        sentiment = "中性"
        suggestion = "估值处于中位区间，按既定策略执行，注重选股质量。"
        action = "维持仓位"
        color = "green"
    elif avg_pct < 80:
        temperature = "偏热"
        sentiment = "乐观"
        suggestion = "估值进入历史上沿，警惕反馈循环（席勒），逐步减少进攻仓位。"
        action = "谨慎 / 减仓部分高估个股"
        color = "orange"
    else:
        temperature = "过热"
        sentiment = "贪婪"
        suggestion = "席勒：媒体狂欢、散户涌入往往出现在顶部。CAPE 处于高位需高度警惕。"
        action = "防御为主 / 大幅降低仓位"
        color = "red"

    return {
        "temperature": temperature,
        "sentiment": sentiment,
        "avg_percentile": round(avg_pct, 1),
        "suggestion": suggestion,
        "action": action,
        "color": color,
        "references": [
            {"book": "投资最重要的事", "principle": "理解市场周期"},
            {"book": "非理性繁荣", "principle": "反馈循环与CAPE"},
        ],
    }
