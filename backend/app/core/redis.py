"""
Redis Client Module
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client = None
_mock_mode = os.getenv("MOCK_REDIS", "true").lower() == "true"


class MockRedis:
    """Mock Redis for development without actual Redis"""

    def __init__(self):
        self._data = {}
        self._expiry = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def set(self, key: str, value, ex=None):
        self._data[key] = value
        return True

    async def setex(self, key: str, seconds: int, value):
        self._data[key] = value
        return True

    async def hgetall(self, key: str):
        return self._data.get(key, {})

    async def hset(self, key: str, mapping: dict = None, **kwargs):
        if key not in self._data:
            self._data[key] = {}
        if mapping:
            self._data[key].update(mapping)
        self._data[key].update(kwargs)
        return True

    async def expire(self, key: str, seconds: int):
        return True

    async def delete(self, key: str):
        self._data.pop(key, None)
        return True

    async def ping(self):
        return True

    async def close(self):
        pass


async def init_redis():
    """Initialize Redis connection"""
    global _redis_client

    if _mock_mode:
        _redis_client = MockRedis()
        logger.info("Using mock Redis (development mode)")
        return

    try:
        import redis.asyncio as redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed, using mock: {e}")
        _redis_client = MockRedis()


async def get_redis():
    """Get Redis client instance"""
    global _redis_client
    if _redis_client is None:
        await init_redis()
    return _redis_client


async def close_redis():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")
