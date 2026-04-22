from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class StockInfo(BaseModel):
    """股票基本信息"""
    code: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None

    class Config:
        from_attributes = True


class StockListItem(BaseModel):
    """股票列表项"""
    code: str
    name: str


class RealtimeData(BaseModel):
    """实时行情数据"""
    code: str
    name: str
    price: float
    open: float
    high: float
    low: float
    volume: int
    amount: float
    change: float
    change_percent: float
    timestamp: Optional[datetime] = None


class HistoryData(BaseModel):
    """历史K线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: int
    amount: float
    change_percent: float


class ComparisonData(BaseModel):
    """对比数据"""
    code: str
    name: str
    data: List[dict]  # 日期和收益率/价格


class ComparisonRequest(BaseModel):
    """对比请求"""
    codes: str = Field(..., description="股票代码，逗号分隔，如: 600519,000858")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    normalize: bool = True  # 是否归一化（计算收益率）


class ComparisonResponse(BaseModel):
    """对比响应"""
    stocks: List[ComparisonData]
    start_date: str
    end_date: str


# ========== 基金相关模型 ==========

class FundInfo(BaseModel):
    """基金基本信息"""
    code: str
    name: str
    fund_type: Optional[str] = None

    class Config:
        from_attributes = True


class FundListItem(BaseModel):
    """基金列表项"""
    code: str
    name: str
    type: Optional[str] = None


class FundHistoryData(BaseModel):
    """基金历史净值数据"""
    date: str
    nav: float
    change_percent: float


class FundComparisonData(BaseModel):
    """基金对比数据"""
    code: str
    name: str
    data: List[dict]


class FundComparisonResponse(BaseModel):
    """基金对比响应"""
    funds: List[FundComparisonData]
    start_date: str
    end_date: str


# ========== 板块相关模型 ==========

class SectorInfo(BaseModel):
    """板块基本信息"""
    code: str
    name: str
    price: Optional[float] = None
    change_percent: Optional[float] = None
    change_amount: Optional[float] = None
    total_market_cap: Optional[float] = None
    turnover_rate: Optional[float] = 0
    up_count: Optional[int] = 0
    down_count: Optional[int] = 0
    leading_stock: Optional[str] = ""
    leading_stock_change: Optional[float] = 0
    historical_change: Optional[float] = None


class SectorFundItem(BaseModel):
    """板块基金项（按涨幅排序）"""
    code: str
    name: str
    fund_type: Optional[str] = None
    nav: Optional[float] = None
    nav_date: Optional[str] = None
    daily_change: Optional[float] = None
    week_change: Optional[float] = None
    month_change: Optional[float] = None
    three_month_change: Optional[float] = None
    six_month_change: Optional[float] = None
    year_change: Optional[float] = None
    total_change: Optional[float] = None


# ========== 量化分析相关模型 ==========

class SmartScreenItem(BaseModel):
    """智能选股结果项"""
    code: str
    name: str
    price: Optional[float] = 0
    change_percent: Optional[float] = 0
    turnover_rate: Optional[float] = 0
    screen_type: Optional[str] = ""
    screen_label: Optional[str] = ""


class HotStockItem(BaseModel):
    """人气榜结果项"""
    rank: Optional[int] = 0
    code: str
    name: str
    price: Optional[float] = 0
    change_percent: Optional[float] = 0
    hot_rank: Optional[int] = 0


class MarketValuation(BaseModel):
    """市场估值统计"""
    pe_ttm_median: Optional[float] = 0
    pb_median: Optional[float] = 0
    dividend_yield: Optional[float] = 0
    broken_net_count: Optional[int] = 0
    total_count: Optional[int] = 0
    pe_percentile: Optional[float] = 0
    pb_percentile: Optional[float] = 0


class FundamentalFilter(BaseModel):
    """多因子筛选条件"""
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    pb_min: Optional[float] = None
    pb_max: Optional[float] = None
    roe_min: Optional[float] = None
    revenue_growth_min: Optional[float] = None
    net_profit_growth_min: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    debt_ratio_max: Optional[float] = None


class StockScoreItem(BaseModel):
    """股票评分项"""
    code: str
    name: Optional[str] = ""
    pe_ttm: Optional[float] = 0
    pb: Optional[float] = 0
    roe: Optional[float] = 0
    net_profit_margin: Optional[float] = 0
    revenue_growth: Optional[float] = 0
    net_profit_growth: Optional[float] = 0
    debt_ratio: Optional[float] = 0
    dividend_yield: Optional[float] = 0
    valuation_score: Optional[float] = 0
    profit_score: Optional[float] = 0
    growth_score: Optional[float] = 0
    debt_score: Optional[float] = 0
    dividend_score: Optional[float] = 0
    total_score: Optional[float] = 0


class FundRecommendItem(BaseModel):
    """基金推荐项"""
    code: str
    name: str
    fund_type: Optional[str] = ""
    nav: Optional[float] = 0
    daily_change: Optional[float] = 0
    week_change: Optional[float] = 0
    month_change: Optional[float] = 0
    three_month_change: Optional[float] = 0
    six_month_change: Optional[float] = 0
    year_change: Optional[float] = 0
    total_change: Optional[float] = 0
    fund_score: Optional[float] = 0
