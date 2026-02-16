"""
Memory Repository 单元测试
=========================

测试 SQLiteMemoryRepository 的 CRUD 操作

运行: pytest tests/test_memory_repository.py -v
"""

import pytest
import asyncio
from datetime import datetime


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestMemoryRepository:
    """Memory Repository 测试"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self):
        """测试存储和检索记忆"""
        from app.core.db.sqlite_impl import init_sqlite, SQLiteMemoryRepository
        import app.core.db.sqlite_impl as sqlite_impl
        
        # Initialize database
        await init_sqlite()
        
        async with sqlite_impl._session_factory() as session:
            repo = SQLiteMemoryRepository(session)
            
            # Store a memory
            memory = await repo.store(
                user_id="test-user-1",
                character_id="luna",
                content="User mentioned they love coffee",
                memory_type="preference",
                importance=0.8,
                metadata={"key_dialogue": ["I love coffee!"]}
            )
            
            assert memory is not None
            assert memory["user_id"] == "test-user-1"
            assert memory["character_id"] == "luna"
            assert memory["summary"] == "User mentioned they love coffee"
            assert memory["event_type"] == "preference"
            
            await session.commit()
            
            # Retrieve memories
            memories = await repo.get_by_user_character(
                user_id="test-user-1",
                character_id="luna"
            )
            
            assert len(memories) >= 1
            assert any(m["summary"] == "User mentioned they love coffee" for m in memories)
    
    @pytest.mark.asyncio
    async def test_get_important_memories(self):
        """测试获取重要记忆"""
        from app.core.db.sqlite_impl import init_sqlite, _session_factory, SQLiteMemoryRepository
        
        await init_sqlite()
        
        async with _session_factory() as session:
            repo = SQLiteMemoryRepository(session)
            
            # Store memories with different importance
            await repo.store(
                user_id="test-user-2",
                character_id="luna",
                content="Low importance memory",
                importance=0.2,
            )
            
            await repo.store(
                user_id="test-user-2",
                character_id="luna",
                content="High importance memory - confession",
                memory_type="confession",
                importance=0.9,
            )
            
            await session.commit()
            
            # Get important memories (importance >= 3)
            important = await repo.get_important(
                user_id="test-user-2",
                character_id="luna",
                min_importance=3
            )
            
            # Should find the confession
            assert any("confession" in m.get("summary", "").lower() or m.get("event_type") == "confession" for m in important)
    
    @pytest.mark.asyncio
    async def test_update_importance(self):
        """测试更新记忆重要性"""
        from app.core.db.sqlite_impl import init_sqlite, _session_factory, SQLiteMemoryRepository
        
        await init_sqlite()
        
        async with _session_factory() as session:
            repo = SQLiteMemoryRepository(session)
            
            # Store a memory
            memory = await repo.store(
                user_id="test-user-3",
                character_id="luna",
                content="Memory to update",
                importance=0.5,
            )
            
            await session.commit()
            
            # Update importance
            success = await repo.update_importance(memory["memory_id"], 0.95)
            assert success
            
            await session.commit()
    
    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """测试删除记忆"""
        from app.core.db.sqlite_impl import init_sqlite, _session_factory, SQLiteMemoryRepository
        
        await init_sqlite()
        
        async with _session_factory() as session:
            repo = SQLiteMemoryRepository(session)
            
            # Store a memory
            memory = await repo.store(
                user_id="test-user-4",
                character_id="luna",
                content="Memory to delete",
                importance=0.5,
            )
            
            await session.commit()
            
            # Delete it
            success = await repo.delete(memory["memory_id"])
            assert success
            
            await session.commit()
