"""
Redis Client Module
==================

Handles Redis connection and operations.

Author: Manus AI
Date: January 28, 2026
"""

import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global _redis_client
    
    _redis_client = redis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )
    
    # Test connection
    try:
        await _redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        Redis client
    """
    if _redis_client is None:
        await init_redis()
    
    return _redis_client


async def close_redis():
    """Close Redis connection"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")
