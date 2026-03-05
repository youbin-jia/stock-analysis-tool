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
    open_price = Column(Float)
    close_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(BigInteger)
    amount = Column(Float)
    change_percent = Column(Float)
    updated_at = Column(DateTime)


# 创建索引
def create_indexes():
    """创建额外的索引以提高查询性能"""
    from sqlalchemy import Index
    Index('idx_stock_date', StockHistory.stock_code, StockHistory.trade_date, unique=True)


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
