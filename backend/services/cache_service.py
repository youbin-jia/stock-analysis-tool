import json
import redis
import os
from typing import Optional, Dict, Any

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# 创建 Redis 连接
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

# 缓存过期时间（秒）
REALTIME_CACHE_TTL = 30  # 实时数据缓存30秒
HISTORY_CACHE_TTL = 3600  # 历史数据缓存1小时


class CacheService:
    """缓存服务类"""

    @staticmethod
    def test_connection() -> bool:
        """测试 Redis 连接"""
        try:
            redis_client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def get_cached_realtime(stock_code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的实时数据"""
        try:
            key = f"realtime:{stock_code}"
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    @staticmethod
    def set_cached_realtime(stock_code: str, data: Dict[str, Any], ttl: int = REALTIME_CACHE_TTL):
        """缓存实时数据"""
        try:
            key = f"realtime:{stock_code}"
            redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            print(f"Redis set error: {e}")

    @staticmethod
    def get_cached_history(stock_code: str, start_date: str, end_date: str) -> Optional[str]:
        """获取缓存的历史数据"""
        try:
            key = f"history:{stock_code}:{start_date}:{end_date}"
            return redis_client.get(key)
        except Exception as e:
            print(f"Redis get history error: {e}")
            return None

    @staticmethod
    def set_cached_history(stock_code: str, start_date: str, end_date: str, data: str,
                          ttl: int = HISTORY_CACHE_TTL):
        """缓存历史数据"""
        try:
            key = f"history:{stock_code}:{start_date}:{end_date}"
            redis_client.setex(key, ttl, data)
        except Exception as e:
            print(f"Redis set history error: {e}")

    @staticmethod
    def invalidate_cache(stock_code: str):
        """清除指定股票的所有缓存"""
        try:
            keys = redis_client.keys(f"*:{stock_code}:*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis invalidate error: {e}")

    @staticmethod
    def batch_set_realtime(data_list: list):
        """批量设置实时数据缓存"""
        try:
            pipe = redis_client.pipeline()
            for item in data_list:
                stock_code = item.get('code')
                if stock_code:
                    key = f"realtime:{stock_code}"
                    pipe.setex(key, REALTIME_CACHE_TTL, json.dumps(item))
            pipe.execute()
        except Exception as e:
            print(f"Redis batch set error: {e}")
