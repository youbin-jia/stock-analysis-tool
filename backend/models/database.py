from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Date, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'stocks.db')}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Stock(Base):
    """股票基本信息表"""
    __tablename__ = "stocks"

    code = Column(String(10), primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    industry = Column(String(50))
    market = Column(String(10))  # SH/SZ
    created_at = Column(DateTime)


class StockHistory(Base):
    """历史K线数据表"""
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    frequency = Column(String(5), index=True, nullable=False, default="d")  # d=日线 w=周线 m=月线
    open_price = Column(Float)
    close_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(BigInteger)
    amount = Column(Float)
    change_percent = Column(Float)
    updated_at = Column(DateTime)


class StockFundamental(Base):
    """股票基本面数据表"""
    __tablename__ = "stock_fundamental"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), index=True, nullable=False)
    date = Column(Date, nullable=False)
    pe_ttm = Column(Float)
    pb = Column(Float)
    roe = Column(Float)
    net_profit_margin = Column(Float)
    revenue_growth = Column(Float)
    net_profit_growth = Column(Float)
    debt_ratio = Column(Float)
    dividend_yield = Column(Float)
    score = Column(Float)


class Fund(Base):
    """基金基本信息表"""
    __tablename__ = "funds"

    code = Column(String(10), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    fund_type = Column(String(30))
    created_at = Column(DateTime)


class FundHistory(Base):
    """基金历史净值数据表"""
    __tablename__ = "fund_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    nav = Column(Float)  # 单位净值
    adjusted_nav = Column(Float)  # 复权净值（考虑份额拆分/分红）
    change_percent = Column(Float)  # 日涨跌幅
    updated_at = Column(DateTime)


def init_database():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
