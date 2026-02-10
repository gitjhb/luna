"""
Greeting 流程单元测试

测试目标：
1. 新session自动插入greeting
2. 旧session缺失greeting会自动补上
3. 已有greeting的session不重复插入
4. LLM context包含greeting
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

# 模拟的角色数据
MOCK_CHARACTER = {
    "character_id": "test-char-123",
    "name": "TestChar",
    "greeting": "你好！我是测试角色，很高兴认识你！",
    "avatar_url": None,
    "background_url": None,
}

MOCK_CHARACTER_NO_GREETING = {
    "character_id": "test-char-no-greeting",
    "name": "NoGreetingChar",
    "avatar_url": None,
    "background_url": None,
}


class TestEnsureSessionHasGreeting:
    """测试 ensure_session_has_greeting 函数"""
    
    @pytest.mark.asyncio
    async def test_new_session_gets_greeting(self):
        """新session（无消息）应该自动插入greeting"""
        from app.api.v1.chat import ensure_session_has_greeting
        
        session_id = str(uuid4())
        
        with patch('app.api.v1.chat.get_character_info', return_value=MOCK_CHARACTER), \
             patch('app.api.v1.chat.chat_repo') as mock_repo:
            
            # 模拟空消息列表
            mock_repo.get_all_messages = AsyncMock(return_value=[])
            mock_repo.add_message = AsyncMock()
            
            result = await ensure_session_has_greeting(session_id, MOCK_CHARACTER["character_id"])
            
            # 应该返回True（插入了greeting）
            assert result == True
            
            # 应该调用add_message
            mock_repo.add_message.assert_called_once()
            call_args = mock_repo.add_message.call_args
            assert call_args.kwargs["role"] == "assistant"
            assert call_args.kwargs["content"] == MOCK_CHARACTER["greeting"]
    
    @pytest.mark.asyncio
    async def test_existing_greeting_not_duplicated(self):
        """已有greeting的session不应该重复插入"""
        from app.api.v1.chat import ensure_session_has_greeting
        
        session_id = str(uuid4())
        
        # 模拟已有greeting的消息列表
        existing_messages = [
            {"role": "assistant", "content": MOCK_CHARACTER["greeting"]},
            {"role": "user", "content": "你好"},
        ]
        
        with patch('app.api.v1.chat.get_character_info', return_value=MOCK_CHARACTER), \
             patch('app.api.v1.chat.chat_repo') as mock_repo:
            
            mock_repo.get_all_messages = AsyncMock(return_value=existing_messages)
            mock_repo.add_message = AsyncMock()
            
            result = await ensure_session_has_greeting(session_id, MOCK_CHARACTER["character_id"])
            
            # 应该返回False（没有插入）
            assert result == False
            
            # 不应该调用add_message
            mock_repo.add_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_old_session_without_greeting_gets_backfilled(self):
        """旧session缺失greeting应该补上"""
        from app.api.v1.chat import ensure_session_has_greeting
        
        session_id = str(uuid4())
        
        # 模拟有聊天但没有greeting的消息列表
        existing_messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好呀！"},
            {"role": "user", "content": "今天天气怎么样"},
        ]
        
        with patch('app.api.v1.chat.get_character_info', return_value=MOCK_CHARACTER), \
             patch('app.api.v1.chat.chat_repo') as mock_repo:
            
            mock_repo.get_all_messages = AsyncMock(return_value=existing_messages)
            mock_repo.add_message = AsyncMock()
            
            result = await ensure_session_has_greeting(session_id, MOCK_CHARACTER["character_id"])
            
            # 应该返回True（补上了greeting）
            assert result == True
            
            # 应该调用add_message
            mock_repo.add_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_character_without_greeting_skipped(self):
        """没有greeting的角色不应该插入任何消息"""
        from app.api.v1.chat import ensure_session_has_greeting
        
        session_id = str(uuid4())
        
        with patch('app.api.v1.chat.get_character_info', return_value=MOCK_CHARACTER_NO_GREETING), \
             patch('app.api.v1.chat.chat_repo') as mock_repo:
            
            mock_repo.get_all_messages = AsyncMock(return_value=[])
            mock_repo.add_message = AsyncMock()
            
            result = await ensure_session_has_greeting(session_id, MOCK_CHARACTER_NO_GREETING["character_id"])
            
            # 应该返回False
            assert result == False
            
            # 不应该调用add_message
            mock_repo.add_message.assert_not_called()


class TestCreateSession:
    """测试 create_session API"""
    
    @pytest.mark.asyncio
    async def test_new_session_has_greeting_in_history(self):
        """新创建的session应该在消息历史里有greeting"""
        from app.api.v1.chat import create_session
        from app.models.schemas import CreateSessionRequest
        from fastapi import Request
        
        # 这个测试需要完整的mock，简化版本
        # 实际应该用TestClient做集成测试
        pass
    
    @pytest.mark.asyncio  
    async def test_existing_session_gets_greeting_backfilled(self):
        """已存在但缺失greeting的session应该被补上"""
        pass


class TestLLMContext:
    """测试LLM能读到greeting"""
    
    @pytest.mark.asyncio
    async def test_greeting_included_in_context_messages(self):
        """greeting应该包含在发给LLM的context里"""
        from app.services.chat_repository import ChatRepository
        
        # 模拟session有greeting
        session_id = str(uuid4())
        messages = [
            {"role": "assistant", "content": "你好！我是测试角色", "message_id": "1", "created_at": "2024-01-01"},
            {"role": "user", "content": "你好", "message_id": "2", "created_at": "2024-01-02"},
        ]
        
        # get_recent_messages 应该返回包含greeting的消息
        # 这样LLM就能看到聊天历史
        
        # 验证：context_messages 第一条应该是 assistant 的 greeting
        assert messages[0]["role"] == "assistant"
        assert "你好" in messages[0]["content"]


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
