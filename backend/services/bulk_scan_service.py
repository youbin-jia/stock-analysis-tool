"""
全市场批量扫描 + 流派 Top 排行
策略：
1. 使用 akshare 的"一次性"接口获取全市场快照（PE/PB/总市值等）
2. 仅对通过初筛的候选股票调用 baostock 补充 ROE/成长/负债数据
3. 用 style_scoring 评分后，按流派排序输出 Top
4. 扫描结果缓存到 Redis（24h）
"""
import akshare as ak
import baostock as bs
import pandas as pd
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from services.cache_service import CacheService
from services.style_scoring import score_all_styles, STYLES


SCAN_STATE_KEY = "bulk_scan:state"
SCAN_RESULT_KEY = "bulk_scan:result"
SCAN_TTL = 86400  # 24h


# ===========================================================
# 状态管理
# ===========================================================

_scan_lock = threading.Lock()
_scan_thread: Optional[threading.Thread] = None


def get_scan_state() -> Dict[str, Any]:
    """获取扫描状态"""
    state = CacheService.get_cached_quant(SCAN_STATE_KEY)
    if not state:
        return {"status": "idle", "progress": 0, "total": 0, "message": "未开始", "updated_at": None}
    return state


def _set_scan_state(status: str, progress: int = 0, total: int = 0, message: str = ""):
    CacheService.set_cached_quant(
        SCAN_STATE_KEY,
        {
            "status": status,
            "progress": progress,
            "total": total,
            "message": message,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
        ttl=SCAN_TTL,
    )


# ===========================================================
# 数据获取
# ===========================================================

def _fetch_market_snapshot_fallback() -> List[Dict[str, Any]]:
    """
    后备路径：使用沪深300 + 中证500 + 中证1000 成分股作为种子池（约 1800 只）
    再用 baostock 批量补 PE/PB。这条路径在东财接口不可用时使用。
    """
    seeds: Dict[str, Dict[str, Any]] = {}

    def _add_index(index_code: str):
        try:
            df = ak.index_stock_cons_csindex(symbol=index_code)
            if df is None or df.empty:
                return
            for _, row in df.iterrows():
                code = str(row.get("成分券代码", row.get("成份券代码", ""))).zfill(6)
                name = str(row.get("成分券名称", row.get("成份券名称", "")))
                if not code or not code.startswith(("6", "0", "3")):
                    continue
                if "ST" in name or "退" in name:
                    continue
                seeds[code] = {
                    "code": code,
                    "name": name,
                    "price": 0,
                    "change_percent": 0,
                    "pe_ttm": 0,
                    "pb": 0,
                    "total_mv": 0,
                    "turnover_rate": 0,
                }
        except Exception as e:
            print(f"取指数成分股失败 {index_code}: {e}")

    for idx in ("000300", "000905", "000852"):  # 沪深300 / 中证500 / 中证1000
        _add_index(idx)

    if not seeds:
        print("种子池为空，无法回退扫描")
        return []
    print(f"种子池: {len(seeds)} 只（沪深300+中证500+中证1000）")

    if not _bs_login():
        return list(seeds.values())

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    codes_list = list(seeds.keys())
    for i, code in enumerate(codes_list):
        try:
            bs_code = _to_bs_code(code)
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,close,peTTM,pbMRQ,turn",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
            )
            last_row = None
            while rs.error_code == "0" and rs.next():
                last_row = rs.get_row_data()
            if last_row:
                try:
                    if last_row[1]:
                        seeds[code]["price"] = round(float(last_row[1]), 2)
                    if last_row[2]:
                        seeds[code]["pe_ttm"] = round(float(last_row[2]), 2)
                    if last_row[3]:
                        seeds[code]["pb"] = round(float(last_row[3]), 2)
                    if len(last_row) > 4 and last_row[4]:
                        seeds[code]["turnover_rate"] = float(last_row[4])
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass
        if (i + 1) % 100 == 0:
            _set_scan_state("running", i + 1, len(codes_list), f"补充估值 {i+1}/{len(codes_list)}")

    _bs_logout()
    # 给一个虚拟"总市值"用于排序：种子池里按沪深300>500>1000 优先级
    return list(seeds.values())


def _fetch_market_snapshot() -> List[Dict[str, Any]]:
    """
    一次性获取全市场快照（PE、PB、总市值、价格、涨跌幅）。
    返回 [{code, name, price, pe_ttm, pb, total_mv, change_percent}, ...]
    """
    result = []

    # 实时行情 + 部分估值（带重试 + 多接口后备）
    df = None
    last_err = None
    import time
    sources = [
        ("stock_zh_a_spot_em", lambda: ak.stock_zh_a_spot_em()),
        ("stock_sh_a_spot_em", lambda: ak.stock_sh_a_spot_em()),
    ]
    for src_name, src_fn in sources:
        for attempt in range(5):
            try:
                df = src_fn()
                if df is not None and not df.empty:
                    print(f"市场快照来源: {src_name} ({len(df)} 行)")
                    break
            except Exception as e:
                last_err = e
                print(f"{src_name} 第{attempt+1}次失败: {e}")
                time.sleep(3 + attempt * 2)
        if df is not None and not df.empty:
            break
    if df is None or df.empty:
        print(f"东财接口失败，回退新浪行情+单只补充估值: {last_err}")
        return _fetch_market_snapshot_fallback()

    try:
        # 列名: 代码 / 名称 / 最新价 / 涨跌幅 / 市盈率-动态 / 市净率 / 总市值 / 流通市值 / 换手率 / ...
        col_map = {}
        for c in df.columns:
            if c == "代码":
                col_map["code"] = c
            elif c == "名称":
                col_map["name"] = c
            elif c == "最新价":
                col_map["price"] = c
            elif c == "涨跌幅":
                col_map["change_percent"] = c
            elif "市盈率" in c and "动态" in c:
                col_map["pe_ttm"] = c
            elif c == "市净率":
                col_map["pb"] = c
            elif c == "总市值":
                col_map["total_mv"] = c
            elif c == "换手率":
                col_map["turnover_rate"] = c

        def _f(v):
            try:
                v = float(v)
                return v if v == v else 0  # NaN check
            except (TypeError, ValueError):
                return 0

        for _, row in df.iterrows():
            code = str(row[col_map.get("code", "代码")]).zfill(6)
            name = str(row[col_map.get("name", "名称")])
            # 过滤 ST、退市、北交所（8开头）
            if "ST" in name or "退" in name:
                continue
            if not code.startswith(("6", "0", "3")):
                continue

            pe = _f(row[col_map["pe_ttm"]]) if "pe_ttm" in col_map else 0
            pb = _f(row[col_map["pb"]]) if "pb" in col_map else 0

            result.append({
                "code": code,
                "name": name,
                "price": _f(row[col_map["price"]]) if "price" in col_map else 0,
                "change_percent": _f(row[col_map["change_percent"]]) if "change_percent" in col_map else 0,
                "pe_ttm": round(pe, 2) if pe > 0 else 0,
                "pb": round(pb, 2) if pb > 0 else 0,
                "total_mv": _f(row[col_map["total_mv"]]) if "total_mv" in col_map else 0,
                "turnover_rate": _f(row[col_map["turnover_rate"]]) if "turnover_rate" in col_map else 0,
            })
    except Exception as e:
        print(f"获取市场快照失败: {e}")

    return result


def _fetch_dividend_yields() -> Dict[str, float]:
    """
    一次性获取股息率（akshare 没有简单的全市场股息率接口，跳过这一项，
    在最终评分时股息率为 0；如需要可后续补充）。
    """
    return {}


def _bs_login():
    try:
        lg = bs.login()
        return lg.error_code == "0"
    except Exception:
        return False


def _bs_logout():
    try:
        bs.logout()
    except Exception:
        pass


def _to_bs_code(code: str) -> str:
    prefix = "sh" if code.startswith("6") else "sz"
    return f"{prefix}.{code}"


def _fetch_bs_fundamentals(code: str, year: int, quarter: int) -> Dict[str, Any]:
    """从 baostock 补充 ROE / 营收增速 / 利润增速 / 负债率 / 净利率"""
    out = {
        "roe": 0, "net_profit_margin": 0,
        "revenue_growth": 0, "net_profit_growth": 0,
        "debt_ratio": 0,
    }
    bs_code = _to_bs_code(code)

    try:
        rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
        # 字段: code, pubDate, statDate, roeAvg, npMargin, gpMargin, netProfit, epsTTM, MBRevenue, totalShare, liqaShare
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            try:
                if len(row) > 3 and row[3]:
                    out["roe"] = float(row[3])
                if len(row) > 4 and row[4]:
                    out["net_profit_margin"] = float(row[4])
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    try:
        rs = bs.query_growth_data(code=bs_code, year=year, quarter=quarter)
        # 字段: code, pubDate, statDate, YOYEquity, YOYAsset, YOYNI, YOYEPSBasic, YOYPNI
        # 注: baostock 无营收同比，用资产同比近似（或留 0）
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            try:
                if len(row) > 4 and row[4]:
                    out["revenue_growth"] = float(row[4])  # YOYAsset 近似营收增速
                if len(row) > 5 and row[5]:
                    out["net_profit_growth"] = float(row[5])  # YOYNI 净利润增速
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    try:
        rs = bs.query_balance_data(code=bs_code, year=year, quarter=quarter)
        # 字段: code, pubDate, statDate, currentRatio, quickRatio, cashRatio, YOYLiability, liabilityToAsset, assetToEquity
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            try:
                if len(row) > 7 and row[7]:
                    out["debt_ratio"] = float(row[7])  # liabilityToAsset 资产负债率
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    return out


# ===========================================================
# 候选股初筛 - 对每个流派的"硬门槛"，减少 baostock 调用
# ===========================================================

def _initial_filter(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    用市场快照里已有的 PE/PB 做硬门槛初筛，保留可能进入任一流派 Top 的股票。
    保留条件（满足任一即保留）：
      - PE 在 (0, 60]
      - PB 在 (0, 5]
      - 总市值 > 100 亿（若有市值数据）
    后备路径下 total_mv=0，仅靠 PE/PB 筛选。
    """
    candidates = []
    for s in stocks:
        mv = s.get("total_mv", 0)
        # 若有市值数据，过滤掉小于 20 亿的
        if mv > 0 and mv < 2_000_000_000:
            continue
        pe_ok = 0 < s["pe_ttm"] <= 60
        pb_ok = 0 < s["pb"] <= 5
        big_cap = mv > 10_000_000_000  # 100 亿
        if pe_ok or pb_ok or big_cap:
            candidates.append(s)
    return candidates


# ===========================================================
# 主扫描流程
# ===========================================================

def _do_scan(max_candidates: int = 800):
    """实际扫描逻辑（同步、耗时）"""
    try:
        _set_scan_state("running", 0, 0, "拉取全市场快照...")
        snapshot = _fetch_market_snapshot()
        if not snapshot:
            _set_scan_state("failed", 0, 0, "无法获取市场快照")
            return

        _set_scan_state("running", 0, len(snapshot), f"快照已加载 {len(snapshot)} 只，开始初筛...")
        candidates = _initial_filter(snapshot)
        # 按总市值降序，优先扫描大盘股
        candidates.sort(key=lambda x: x["total_mv"], reverse=True)
        candidates = candidates[:max_candidates]

        _set_scan_state("running", 0, len(candidates), f"初筛后剩 {len(candidates)} 只，补充财务数据...")

        # 计算 baostock 查询时间窗
        now = datetime.now()
        year = now.year
        quarter = (now.month - 1) // 3
        if quarter == 0:
            year -= 1
            quarter = 4

        if not _bs_login():
            print("baostock 登录失败，仅使用 akshare 数据")

        enriched = []
        for i, s in enumerate(candidates):
            try:
                fund = _fetch_bs_fundamentals(s["code"], year, quarter)
                merged = {**s, **fund, "dividend_yield": 0}
                enriched.append(merged)
            except Exception as e:
                print(f"补充财务失败 {s['code']}: {e}")
            if (i + 1) % 20 == 0:
                _set_scan_state(
                    "running", i + 1, len(candidates),
                    f"已处理 {i + 1}/{len(candidates)}"
                )

        _bs_logout()

        # 对每个候选股计算 4 流派评分
        _set_scan_state("running", len(candidates), len(candidates), "计算流派评分...")
        scored_all = []
        for d in enriched:
            try:
                s_result = score_all_styles(d)
                scored_all.append({
                    "code": d["code"],
                    "name": d["name"],
                    "price": d["price"],
                    "change_percent": d["change_percent"],
                    "total_mv": d["total_mv"],
                    "pe_ttm": d["pe_ttm"],
                    "pb": d["pb"],
                    "roe": d.get("roe", 0),
                    "net_profit_margin": d.get("net_profit_margin", 0),
                    "revenue_growth": d.get("revenue_growth", 0),
                    "net_profit_growth": d.get("net_profit_growth", 0),
                    "debt_ratio": d.get("debt_ratio", 0),
                    "composite_score": s_result["composite_score"],
                    "best_style": s_result["best_style"],
                    "style_scores": {
                        item["key"]: {
                            "score": item["score"],
                            "passed_count": item["passed_count"],
                            "total_rules": item["total_rules"],
                        }
                        for item in s_result["styles"]
                    },
                })
            except Exception as e:
                print(f"评分失败 {d['code']}: {e}")

        # 按每个流派取 Top
        style_tops = {}
        for style_key in STYLES.keys():
            ranked = sorted(
                scored_all,
                key=lambda x: x["style_scores"].get(style_key, {}).get("score", 0),
                reverse=True,
            )
            # 至少要通过 3 条规则才算合格
            qualified = [
                r for r in ranked
                if r["style_scores"].get(style_key, {}).get("passed_count", 0) >= 3
            ]
            style_tops[style_key] = qualified[:30]

        result = {
            "scanned_at": datetime.now().isoformat(timespec="seconds"),
            "total_stocks": len(snapshot),
            "candidates": len(candidates),
            "scored": len(scored_all),
            "style_tops": style_tops,
        }

        CacheService.set_cached_quant(SCAN_RESULT_KEY, result, ttl=SCAN_TTL)
        _set_scan_state(
            "done", len(candidates), len(candidates),
            f"扫描完成：共评分 {len(scored_all)} 只"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_scan_state("failed", 0, 0, f"扫描失败: {e}")


def start_scan_async(max_candidates: int = 800) -> bool:
    """异步启动扫描，返回是否成功启动"""
    global _scan_thread
    with _scan_lock:
        if _scan_thread is not None and _scan_thread.is_alive():
            return False
        _scan_thread = threading.Thread(
            target=_do_scan, args=(max_candidates,), daemon=True
        )
        _scan_thread.start()
        return True


def get_scan_result() -> Optional[Dict[str, Any]]:
    """获取最近一次扫描结果"""
    return CacheService.get_cached_quant(SCAN_RESULT_KEY)


def get_style_top(style_key: str, limit: int = 10) -> Dict[str, Any]:
    """获取指定流派的 Top N"""
    result = get_scan_result()
    if not result:
        return {"style": style_key, "data": [], "scanned_at": None, "available": False}

    if style_key not in STYLES:
        return {"style": style_key, "data": [], "scanned_at": result["scanned_at"], "available": True}

    tops = result["style_tops"].get(style_key, [])[:limit]
    return {
        "style": style_key,
        "style_name": STYLES[style_key]["name"],
        "key_principle": STYLES[style_key]["key_principle"],
        "data": tops,
        "scanned_at": result["scanned_at"],
        "total_scored": result["scored"],
        "available": True,
    }


def get_all_style_tops(limit: int = 10) -> Dict[str, Any]:
    """一次返回 4 流派各自 Top N"""
    result = get_scan_result()
    if not result:
        return {"available": False, "scanned_at": None, "tops": {}}

    return {
        "available": True,
        "scanned_at": result["scanned_at"],
        "total_stocks": result["total_stocks"],
        "candidates": result["candidates"],
        "total_scored": result["scored"],
        "tops": {
            key: {
                "style_name": STYLES[key]["name"],
                "key_principle": STYLES[key]["key_principle"],
                "books": STYLES[key]["books"],
                "data": result["style_tops"].get(key, [])[:limit],
            }
            for key in STYLES.keys()
        },
    }
