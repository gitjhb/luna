"""
Tenacity-compatible retry utilities for Vercel deployment.
Drop-in replacement for tenacity with minimal functionality.
"""

import asyncio
import functools
import logging
from typing import Callable, Type, Tuple, Any

logger = logging.getLogger(__name__)


class stop_after_attempt:
    """Stop after N attempts."""
    def __init__(self, max_attempts: int):
        self.max_attempts = max_attempts


class wait_exponential:
    """Exponential backoff wait strategy."""
    def __init__(self, multiplier: float = 1, min: float = 0, max: float = 60):
        self.multiplier = multiplier
        self.min = min
        self.max = max
    
    def __call__(self, attempt: int) -> float:
        wait_time = self.multiplier * (2 ** attempt)
        return min(max(wait_time, self.min), self.max)


def retry(
    stop: stop_after_attempt = None,
    wait: wait_exponential = None,
    reraise: bool = True,
):
    """
    Tenacity-compatible retry decorator.
    Supports both sync and async functions.
    """
    max_attempts = stop.max_attempts if stop else 3
    wait_strategy = wait or wait_exponential()
    
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            wait_time = wait_strategy(attempt)
                            logger.warning(
                                f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                                f"after {wait_time:.1f}s: {e}"
                            )
                            await asyncio.sleep(wait_time)
                if reraise and last_exception:
                    raise last_exception
                return None
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                import time
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            wait_time = wait_strategy(attempt)
                            logger.warning(
                                f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                                f"after {wait_time:.1f}s: {e}"
                            )
                            time.sleep(wait_time)
                if reraise and last_exception:
                    raise last_exception
                return None
            return sync_wrapper
    return decorator
