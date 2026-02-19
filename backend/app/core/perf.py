"""
Performance Tracking Utilities
==============================

提供简洁的性能追踪工具，用于测量关键 API 的响应时间。

Usage:
    # Context Manager
    async with PerfTimer("llm_call") as timer:
        result = await llm.call()
    # timer.elapsed_ms 可用
    
    # 装饰器
    @perf_track("db_query")
    async def get_user():
        ...
    
    # 批量追踪
    tracker = PerfTracker()
    with tracker.track("precompute"):
        ...
    with tracker.track("llm"):
        ...
    tracker.log_summary("chat")  # [PERF] chat: 1.23s (precompute: 0.12s, llm: 1.05s)
"""

import time
import logging
import functools
from typing import Optional, Dict
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)


class PerfTimer:
    """简单的计时器，支持 context manager"""
    
    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed: float = 0  # seconds
        self.elapsed_ms: float = 0  # milliseconds
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        self.elapsed_ms = self.elapsed * 1000
        return False
    
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        self.elapsed_ms = self.elapsed * 1000
        return False


class PerfTracker:
    """
    批量性能追踪器，用于追踪一个请求中的多个阶段。
    
    Example:
        tracker = PerfTracker()
        
        with tracker.track("precompute"):
            precompute_result = precompute_service.analyze(...)
        
        async with tracker.track_async("llm"):
            response = await llm.call(...)
        
        tracker.log_summary("chat")
        # Output: [PERF] chat: 1.23s (precompute: 0.12s, llm: 1.05s)
    """
    
    def __init__(self):
        self.stages: Dict[str, float] = {}  # name -> elapsed seconds
        self.start_time: float = time.perf_counter()
    
    @contextmanager
    def track(self, name: str):
        """同步追踪一个阶段"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.stages[name] = elapsed
    
    @asynccontextmanager
    async def track_async(self, name: str):
        """异步追踪一个阶段"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.stages[name] = elapsed
    
    def mark(self, name: str, elapsed: float):
        """手动记录一个阶段的耗时（秒）"""
        self.stages[name] = elapsed
    
    @property
    def total_elapsed(self) -> float:
        """从创建到现在的总耗时（秒）"""
        return time.perf_counter() - self.start_time
    
    def get_summary(self, operation: str) -> str:
        """
        生成性能摘要字符串
        
        Args:
            operation: 操作名称（如 "chat"）
            
        Returns:
            格式化的摘要，如 "chat: 1.23s (l1: 0.12s, llm: 1.05s)"
        """
        total = self.total_elapsed
        
        if not self.stages:
            return f"{operation}: {total:.2f}s"
        
        # 格式化各阶段
        stage_parts = []
        for name, elapsed in self.stages.items():
            stage_parts.append(f"{name}: {elapsed:.2f}s")
        
        stages_str = ", ".join(stage_parts)
        return f"{operation}: {total:.2f}s ({stages_str})"
    
    def log_summary(self, operation: str, level: str = "INFO"):
        """
        输出性能日志
        
        Args:
            operation: 操作名称
            level: 日志级别 (INFO, DEBUG, WARNING)
        """
        summary = self.get_summary(operation)
        log_msg = f"[PERF] {summary}"
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(log_msg)


def perf_track(name: str):
    """
    性能追踪装饰器，自动记录函数执行时间
    
    Usage:
        @perf_track("get_user")
        async def get_user(user_id: str):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                logger.debug(f"[PERF] {name}: {elapsed:.3f}s")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                logger.debug(f"[PERF] {name}: {elapsed:.3f}s")
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
