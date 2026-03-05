import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
from services.stock_service import StockService
from services.cache_service import CacheService
from services.data_service import DataService
from models.database import init_database

scheduler = AsyncIOScheduler()


def is_trading_time():
    """判断当前是否为交易时间"""
    now = datetime.now()
    current_time = now.time()

    # 交易时间：9:30-11:30, 13:00-15:00
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)


async def update_realtime_data():
    """
    每30秒更新实时行情缓存
    只在交易时间执行
    """
    if not is_trading_time():
        return

    try:
        print(f"[{datetime.now()}] 更新实时行情缓存...")
        data_list = StockService.get_all_realtime_data()
        if data_list:
            CacheService.batch_set_realtime(data_list)
            print(f"已缓存 {len(data_list)} 只股票的实时数据")
    except Exception as e:
        print(f"更新实时行情错误: {e}")


async def update_daily_data():
    """
    每日收盘后更新历史数据
    每日15:30执行
    """
    try:
        print(f"[{datetime.now()}] 更新每日历史数据...")

        # 获取所有股票列表
        stock_list = StockService.get_stock_list()

        # 计算日期范围（昨天到今天）
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        updated_count = 0
        for stock in stock_list[:100]:  # 先更新前100只，避免过载
            code = stock['code']
            try:
                data = StockService.get_historical_data(code, start_date, end_date)
                if data:
                    DataService.save_to_database(code, data)
                    updated_count += 1
            except Exception as e:
                print(f"更新股票 {code} 数据错误: {e}")

        print(f"已更新 {updated_count} 只股票的历史数据")
    except Exception as e:
        print(f"更新每日数据错误: {e}")


async def init_database_and_cache():
    """
    应用启动时初始化数据库和缓存
    """
    try:
        print("初始化数据库...")
        init_database()
        print("数据库初始化完成")

        # 检查Redis连接
        if CacheService.test_connection():
            print("Redis连接正常")
        else:
            print("警告: Redis连接失败，缓存功能将不可用")

    except Exception as e:
        print(f"初始化错误: {e}")


def start_scheduler():
    """
    启动定时任务调度器
    """
    # 每30秒更新实时行情（仅在交易时间）
    scheduler.add_job(
        update_realtime_data,
        'interval',
        seconds=30,
        id='update_realtime',
        replace_existing=True
    )

    # 每日15:30更新历史数据
    scheduler.add_job(
        update_daily_data,
        'cron',
        hour=15,
        minute=30,
        id='update_daily',
        replace_existing=True
    )

    scheduler.start()
    print("定时任务调度器已启动")


def stop_scheduler():
    """
    停止定时任务调度器
    """
    if scheduler.running:
        scheduler.shutdown()
        print("定时任务调度器已停止")


from datetime import timedelta
