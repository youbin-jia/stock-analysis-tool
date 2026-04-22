import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time, timedelta
from services.stock_service import StockService
from services.fund_service import FundService
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
    每日收盘后增量更新历史数据
    每日15:30执行
    """
    try:
        print(f"[{datetime.now()}] 增量更新历史数据...")

        # 获取热门股票列表
        stock_list = StockService.get_stock_list()
        popular_stocks = stock_list[:50]  # 更新前50只热门股票

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        frequencies = [
            ("d", "日线"),
            ("w", "周线"),
            ("m", "月线"),
        ]

        updated_count = 0
        for stock in popular_stocks:
            code = stock['code']
            for freq, freq_name in frequencies:
                try:
                    latest_date = DataService.get_latest_date_in_db(code, freq)

                    if latest_date:
                        # 增量更新：从最新日期的下一天到今天
                        next_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if next_date <= today:
                            data = StockService.get_historical_data(code, next_date, today, freq)
                            if data:
                                DataService.save_to_database(code, data, freq)
                                updated_count += 1
                                print(f"  更新 {code} {freq_name}: {len(data)} 条")
                    else:
                        # 首次下载：拉取近10年数据（覆盖 period=all 的需求）
                        start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
                        data = StockService.get_historical_data(code, start_date, today, freq)
                        if data:
                            DataService.save_to_database(code, data, freq)
                            updated_count += 1
                            print(f"  首次下载 {code} {freq_name}: {len(data)} 条")
                except Exception as e:
                    print(f"  更新股票 {code} {freq_name} 错误: {e}")

        print(f"已更新 {updated_count} 组历史数据")
    except Exception as e:
        print(f"更新每日数据错误: {e}")


async def update_fund_data():
    """
    每日更新基金历史净值数据
    每日 16:00 执行（基金净值通常在15:00收盘后更新）
    """
    try:
        print(f"[{datetime.now()}] 增量更新基金净值数据...")

        # 获取基金列表（优先从缓存）
        fund_list = FundService.get_fund_list()
        if not fund_list:
            print("获取基金列表失败，跳过更新")
            return

        # 缓存基金列表到 Redis
        CacheService.set_cached_fund_list(fund_list)

        # 只更新前 100 只热门基金（控制请求量）
        popular_funds = fund_list[:100]

        today = datetime.now().strftime("%Y-%m-%d")
        updated_count = 0

        for fund in popular_funds:
            code = fund['code']
            try:
                latest_date = DataService.get_fund_latest_date_in_db(code)

                if latest_date:
                    # 增量更新
                    next_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    if next_date <= today:
                        data = FundService.get_fund_history(code, next_date, today)
                        if data:
                            DataService.save_fund_to_database(code, data)
                            updated_count += 1
                            print(f"  更新基金 {code}: {len(data)} 条")
                else:
                    # 首次下载：拉取全部历史数据（eastmoney 一次返回全部，调用成本相同）
                    data = FundService.get_fund_history(code, None, None)
                    if data:
                        DataService.save_fund_to_database(code, data)
                        updated_count += 1
                        print(f"  首次下载基金 {code}: {len(data)} 条（全部历史）")
            except Exception as e:
                print(f"  更新基金 {code} 错误: {e}")

        print(f"已更新 {updated_count} 只基金净值数据")
    except Exception as e:
        print(f"更新基金数据错误: {e}")


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

    # 每日15:30增量更新历史数据
    scheduler.add_job(
        update_daily_data,
        'cron',
        hour=15,
        minute=30,
        id='update_daily',
        replace_existing=True
    )

    # 每日16:00增量更新基金净值数据
    scheduler.add_job(
        update_fund_data,
        'cron',
        hour=16,
        minute=0,
        id='update_fund',
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
