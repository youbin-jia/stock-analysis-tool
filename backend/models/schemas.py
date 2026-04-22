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
