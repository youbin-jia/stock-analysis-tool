"""
政策信息收集与 LLM 总结服务

数据源：
- 求是网（http://www.qstheory.cn）
- 新华网时政（http://www.news.cn）
- 中国政府网政策（http://www.gov.cn）

合规说明：
- 文章正文仅在分析时临时使用，不持久化、不在前端展示原文
- 前端只展示：标题、来源、日期、链接、AI 生成的简短摘要与方向推断
"""
import os
import re
import json
import time
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from services.cache_service import CacheService


KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE = "https://api.moonshot.cn/v1"
KIMI_MODEL = "moonshot-v1-32k"

POLICY_STATE_KEY = "policy_scan:state"
POLICY_RESULT_KEY = "policy_scan:result"
POLICY_TTL = 6 * 3600  # 6h

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

_scan_lock = threading.Lock()
_scan_thread: Optional[threading.Thread] = None


# =========================================================
# 状态管理
# =========================================================

def get_scan_state() -> Dict[str, Any]:
    state = CacheService.get_cached_quant(POLICY_STATE_KEY)
    if not state:
        return {"status": "idle", "progress": 0, "total": 0, "message": "未开始", "updated_at": None}
    return state


def _set_state(status: str, progress: int = 0, total: int = 0, message: str = ""):
    CacheService.set_cached_quant(
        POLICY_STATE_KEY,
        {
            "status": status,
            "progress": progress,
            "total": total,
            "message": message,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
        ttl=POLICY_TTL,
    )


# =========================================================
# 抓取
# =========================================================

def _http_get(url: str, timeout: int = 15) -> Optional[str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.encoding = r.apparent_encoding or "utf-8"
        if r.status_code == 200:
            return r.text
        print(f"GET {url} 状态码 {r.status_code}")
    except Exception as e:
        print(f"GET 失败 {url}: {e}")
    return None


def _parse_date(text: str) -> Optional[str]:
    """从文本中提取日期 YYYY-MM-DD"""
    if not text:
        return None
    # 各种格式
    patterns = [
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})",
        r"(\d{4})\.(\d{1,2})\.(\d{1,2})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            y, mo, d = m.groups()
            try:
                return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            except ValueError:
                continue
    return None


def _within_days(date_str: Optional[str], days: int) -> bool:
    if not date_str:
        return True  # 未知日期保守保留
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - d).days <= days
    except ValueError:
        return True


def fetch_qstheory_list(limit: int = 30) -> List[Dict[str, Any]]:
    """求是网最新文章。新版 URL 模式：/YYYYMMDD/<hash>/c.html"""
    articles = []
    urls = [
        "http://www.qstheory.cn",                         # 首页（含最新）
        "http://www.qstheory.cn/qsyw/index.htm",          # 要闻
        "http://www.qstheory.cn/qszq/zywz/index.htm",     # 重要文章
    ]
    seen = set()
    # 紧凑日期 /20YYMMDD/<hash>/c.htm(l)  或  老式 /20YY-MM/DD/...c_NNN.htm
    pat_new = re.compile(r"/(20\d{6})/[0-9a-f]+/c\.html?$")
    pat_old = re.compile(r"/(20\d{2})-(\d{2})/(\d{2})/[^/]+\.html?$")
    for url in urls:
        html = _http_get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not title or len(title) < 8 or len(title) > 120:
                continue
            if "javascript" in href.lower():
                continue
            if "en.qstheory.cn" in href:
                continue
            # 解析为绝对 URL
            if href.startswith("//"):
                full = "http:" + href
            elif href.startswith("/"):
                full = "http://www.qstheory.cn" + href
            elif href.startswith("http"):
                full = href
            elif re.match(r"^\d{8}/", href):
                # 相对路径如 20260618/xxx/c.html
                full = "http://www.qstheory.cn/" + href
            else:
                continue
            if "qstheory.cn" not in full:
                continue

            # 提取日期
            date = None
            m = pat_new.search(full)
            if m:
                d = m.group(1)
                date = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
            else:
                m2 = pat_old.search(full)
                if m2:
                    date = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
                else:
                    continue  # 非文章详情

            if full in seen:
                continue
            seen.add(full)
            articles.append({
                "title": title,
                "url": full,
                "source": "求是网",
                "date": date,
            })
            if len(articles) >= limit:
                break
        if len(articles) >= limit:
            break
    # 按日期降序
    articles.sort(key=lambda x: x.get("date") or "", reverse=True)
    return articles[:limit]


def fetch_gov_policy_list(limit: int = 20) -> List[Dict[str, Any]]:
    """中国政府网政策文件"""
    articles = []
    urls = [
        "http://www.gov.cn/zhengce/zuixin.htm",
        "https://www.gov.cn/zhengce/",
    ]
    seen = set()
    for url in urls:
        html = _http_get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not title or len(title) < 10 or len(title) > 100:
                continue
            if href.startswith("/"):
                full = "https://www.gov.cn" + href
            elif href.startswith("http"):
                full = href
            else:
                continue
            if "gov.cn" not in full:
                continue
            if not re.search(r"/content_\d+|/202\d", full):
                continue
            if full in seen:
                continue
            seen.add(full)
            date = _parse_date(full) or _parse_date(title)
            articles.append({
                "title": title,
                "url": full,
                "source": "中国政府网",
                "date": date,
            })
            if len(articles) >= limit:
                break
        if len(articles) >= limit:
            break
    return articles


def fetch_xinhua_list(limit: int = 20) -> List[Dict[str, Any]]:
    """新华网时政"""
    articles = []
    urls = [
        "http://www.news.cn/politics/index.htm",
        "http://www.xinhuanet.com/politics/",
    ]
    seen = set()
    for url in urls:
        html = _http_get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not title or len(title) < 10 or len(title) > 100:
                continue
            if "javascript" in href.lower():
                continue
            if href.startswith("//"):
                full = "http:" + href
            elif href.startswith("/"):
                full = "http://www.news.cn" + href
            elif href.startswith("http"):
                full = href
            else:
                continue
            if "news.cn" not in full and "xinhuanet" not in full:
                continue
            if not re.search(r"/202\d", full):
                continue
            if full in seen:
                continue
            seen.add(full)
            date = _parse_date(full)
            articles.append({
                "title": title,
                "url": full,
                "source": "新华网",
                "date": date,
            })
            if len(articles) >= limit:
                break
        if len(articles) >= limit:
            break
    return articles


def fetch_article_text(url: str, max_len: int = 4000) -> str:
    """抓取文章正文（仅供 LLM 临时分析，不持久化）"""
    html = _http_get(url, timeout=20)
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # 移除脚本/样式
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # 优先找正文 div
    candidates = []
    for sel in [
        {"name": "div", "id": re.compile(r"content|article|main", re.I)},
        {"name": "div", "class_": re.compile(r"content|article|main|TRS_Editor|text", re.I)},
        {"name": "article"},
    ]:
        for el in soup.find_all(**sel):
            txt = el.get_text("\n", strip=True)
            if len(txt) > 200:
                candidates.append(txt)
    if not candidates:
        candidates = [soup.get_text("\n", strip=True)]
    text = max(candidates, key=len)
    # 去除多余空行
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:max_len]


# =========================================================
# Kimi LLM 调用
# =========================================================

def _kimi_chat(messages: List[Dict[str, str]], temperature: float = 0.3, max_retries: int = 2) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": KIMI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(f"{KIMI_BASE}/chat/completions",
                              headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]
            elif r.status_code == 429:
                # rate limit
                time.sleep(8 + attempt * 5)
            else:
                print(f"Kimi 错误 {r.status_code}: {r.text[:200]}")
                return None
        except Exception as e:
            print(f"Kimi 调用异常 第{attempt+1}次: {e}")
            time.sleep(3 + attempt * 2)
    return None


def _extract_json(text: str) -> Optional[Any]:
    """从 LLM 输出中提取 JSON（兼容带代码块的）"""
    if not text:
        return None
    # 优先匹配代码块
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", text)
    if m:
        candidate = m.group(1)
    else:
        # 找第一个 { 或 [
        start_obj = text.find("{")
        start_arr = text.find("[")
        starts = [s for s in (start_obj, start_arr) if s >= 0]
        if not starts:
            return None
        start = min(starts)
        candidate = text[start:]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # 尝试找到匹配的右括号
        try:
            return json.loads(candidate.rsplit("}", 1)[0] + "}")
        except Exception:
            return None


def llm_summarize_article(title: str, source: str, text: str) -> Dict[str, Any]:
    """对单篇文章做结构化摘要"""
    if not text or len(text) < 100:
        return {
            "summary": "",
            "topics": [],
            "industries": [],
            "policy_signal": "",
            "investment_impact": "",
        }

    prompt = f"""你是政策分析助手。请基于以下来自《{source}》的政策文章，输出严格 JSON 结构（不要任何解释文字）：

文章标题：{title}
文章正文（节选）：
{text[:3500]}

请输出 JSON：
{{
  "summary": "用不超过 80 字概括文章核心政策内容",
  "topics": ["主题标签1", "主题标签2"],  // 2-5 个简短主题词，如 "新质生产力" "AI" "半导体"
  "industries": ["行业1", "行业2"],  // 0-4 个 A 股相关行业，如 "电子" "汽车" "医药生物" "通信"
  "policy_signal": "扶持/规范/中性",  // 三选一
  "investment_impact": "用不超过 40 字说明可能的投资影响方向"
}}

只输出 JSON，不要 markdown 代码块。"""

    resp = _kimi_chat([{"role": "user", "content": prompt}])
    parsed = _extract_json(resp) if resp else None
    if not parsed:
        return {
            "summary": "",
            "topics": [],
            "industries": [],
            "policy_signal": "",
            "investment_impact": "",
        }
    # 规范化
    parsed["topics"] = parsed.get("topics", []) if isinstance(parsed.get("topics"), list) else []
    parsed["industries"] = parsed.get("industries", []) if isinstance(parsed.get("industries"), list) else []
    parsed["summary"] = str(parsed.get("summary", ""))[:200]
    parsed["policy_signal"] = str(parsed.get("policy_signal", ""))[:10]
    parsed["investment_impact"] = str(parsed.get("investment_impact", ""))[:150]
    return parsed


def llm_aggregate(articles_with_summary: List[Dict[str, Any]]) -> Dict[str, Any]:
    """基于多篇文章的结构化摘要，做综合方向总结"""
    if not articles_with_summary:
        return {}

    # 只用结构化摘要 + 标题，控制 token
    digest = []
    for a in articles_with_summary[:60]:
        s = a.get("ai", {})
        if not s.get("summary"):
            continue
        digest.append({
            "title": a["title"],
            "source": a["source"],
            "date": a.get("date"),
            "summary": s["summary"],
            "topics": s.get("topics", []),
            "industries": s.get("industries", []),
            "policy_signal": s.get("policy_signal", ""),
            "investment_impact": s.get("investment_impact", ""),
        })

    if not digest:
        return {}

    prompt = f"""你是宏观政策与投资策略分析师。下面是最近一个月中国主流政策媒体（求是、新华、政府网）的政策文章结构化摘要列表（JSON）：

{json.dumps(digest, ensure_ascii=False, indent=1)[:12000]}

请综合分析后输出严格 JSON（不要任何解释文字）：
{{
  "macro_overview": "用不超过 150 字概括最近一个月的政策主基调与导向",
  "key_themes": [
    {{"theme": "主题名", "weight": 数字(出现次数), "description": "30 字内说明", "related_industries": ["行业1","行业2"]}}
  ],  // 5-10 个最重要主题，按 weight 降序
  "investment_directions": [
    {{"direction": "方向名（如：聚焦AI算力国产化）", "rationale": "60 字内逻辑", "industries": ["行业1","行业2"], "risk": "30 字内风险提示"}}
  ],  // 3-6 条可执行投资方向
  "policy_signals": {{"positive": ["受扶持领域..."], "neutral": ["规范类..."], "cautious": ["需警惕领域..."]}},
  "summary_disclaimer": "本总结仅作政策梳理，不构成投资建议"
}}

注意：
1. investment_directions 要可执行、有具体行业指向
2. 严格输出 JSON，不要 markdown 代码块"""

    resp = _kimi_chat([{"role": "user", "content": prompt}], temperature=0.4)
    parsed = _extract_json(resp) if resp else None
    if not parsed:
        return {"raw": resp or "", "error": "解析失败"}
    return parsed


# =========================================================
# 主流程
# =========================================================

def _do_collect(days: int = 30, max_articles: int = 40):
    try:
        _set_state("running", 0, 0, "抓取政策文章列表...")

        all_articles = []
        for fetcher, name in [
            (fetch_qstheory_list, "求是网"),
            (fetch_xinhua_list, "新华网"),
            (fetch_gov_policy_list, "中国政府网"),
        ]:
            try:
                items = fetcher(limit=20)
                print(f"{name} 抓到 {len(items)} 条")
                all_articles.extend(items)
            except Exception as e:
                print(f"抓取 {name} 失败: {e}")

        # 按日期筛选（最近 N 天）
        filtered = [a for a in all_articles if _within_days(a.get("date"), days)]
        # 去重（按 URL）
        seen = set()
        unique = []
        for a in filtered:
            if a["url"] in seen:
                continue
            seen.add(a["url"])
            unique.append(a)

        # 限制总量，按日期降序
        unique.sort(key=lambda x: x.get("date") or "", reverse=True)
        unique = unique[:max_articles]

        if not unique:
            _set_state("failed", 0, 0, "未抓到任何文章（来源站点可能不可访问）")
            return

        total = len(unique)
        _set_state("running", 0, total, f"共 {total} 篇，开始 AI 总结...")

        # 对每篇文章抓正文 + LLM 总结
        results = []
        for i, art in enumerate(unique):
            try:
                text = fetch_article_text(art["url"])
                ai = llm_summarize_article(art["title"], art["source"], text)
                art["ai"] = ai
                results.append(art)
            except Exception as e:
                print(f"分析失败 {art['url']}: {e}")
                art["ai"] = {"summary": "", "topics": [], "industries": [],
                             "policy_signal": "", "investment_impact": ""}
                results.append(art)
            _set_state("running", i + 1, total, f"AI 分析中 {i+1}/{total}")
            # 简单限流
            time.sleep(0.3)

        # 综合总结
        _set_state("running", total, total, "生成月度综合方向总结...")
        aggregate = llm_aggregate(results)

        # 主题热度
        topic_counter = {}
        industry_counter = {}
        signal_counter = {"扶持": 0, "规范": 0, "中性": 0}
        for r in results:
            ai = r.get("ai", {}) or {}
            for t in ai.get("topics", []):
                topic_counter[t] = topic_counter.get(t, 0) + 1
            for ind in ai.get("industries", []):
                industry_counter[ind] = industry_counter.get(ind, 0) + 1
            sig = ai.get("policy_signal", "")
            if sig in signal_counter:
                signal_counter[sig] += 1

        topic_rank = sorted(
            [{"topic": k, "count": v} for k, v in topic_counter.items()],
            key=lambda x: x["count"], reverse=True
        )[:30]
        industry_rank = sorted(
            [{"industry": k, "count": v} for k, v in industry_counter.items()],
            key=lambda x: x["count"], reverse=True
        )[:30]

        # 不保存正文，只保存元数据 + AI 摘要
        articles_clean = [
            {
                "title": r["title"],
                "url": r["url"],
                "source": r["source"],
                "date": r.get("date"),
                "ai": r.get("ai", {}),
            }
            for r in results
        ]

        final = {
            "collected_at": datetime.now().isoformat(timespec="seconds"),
            "days": days,
            "article_count": len(articles_clean),
            "articles": articles_clean,
            "topic_rank": topic_rank,
            "industry_rank": industry_rank,
            "signal_distribution": signal_counter,
            "aggregate": aggregate,
        }
        CacheService.set_cached_quant(POLICY_RESULT_KEY, final, ttl=POLICY_TTL)
        _set_state("done", total, total, f"完成：{len(articles_clean)} 篇分析")
    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_state("failed", 0, 0, f"失败: {e}")


def start_collect_async(days: int = 30, max_articles: int = 40) -> bool:
    global _scan_thread
    with _scan_lock:
        if _scan_thread is not None and _scan_thread.is_alive():
            return False
        _scan_thread = threading.Thread(
            target=_do_collect, args=(days, max_articles), daemon=True
        )
        _scan_thread.start()
        return True


def get_collect_result() -> Optional[Dict[str, Any]]:
    return CacheService.get_cached_quant(POLICY_RESULT_KEY)
