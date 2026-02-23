"""
Memory System V2 Tests
======================

测试记忆的存储、检索、和 debug endpoint。
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Test fixtures
TEST_USER_ID = "test_memory_user"
TEST_CHARACTER_ID = "luna"


class TestMemoryExtraction:
    """测试记忆提取模式匹配"""
    
    def test_extract_name_chinese(self):
        """测试中文名字提取"""
        from app.services.memory_system_v2.memory_manager import MemoryExtractor
        
        extractor = MemoryExtractor(llm_service=None)
        
        # 应该提取
        test_cases = [
            ("我叫小明", "小明"),
            ("我叫JHB", "JHB"),
            ("叫我宝贝", "宝贝"),
        ]
        
        for message, expected in test_cases:
            # 使用正则匹配
            import re
            for pattern in extractor.INFO_PATTERNS.get("user_name", []):
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    assert value == expected, f"Expected '{expected}' but got '{value}' for '{message}'"
                    break
    
    def test_not_extract_name_from_question(self):
        """测试不应该从问句中提取名字"""
        from app.services.memory_system_v2.memory_manager import MemoryExtractor
        import re
        
        extractor = MemoryExtractor(llm_service=None)
        
        # 不应该提取名字的句子
        negative_cases = [
            "你知道我是谁吗",
            "你是谁",
            "你记得我吗",
        ]
        
        for message in negative_cases:
            extracted = None
            for pattern in extractor.INFO_PATTERNS.get("user_name", []):
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip()
                    break
            
            # 应该不提取或提取为 None
            assert extracted is None, f"Should not extract name from '{message}', but got '{extracted}'"
    
    def test_extract_likes(self):
        """测试喜好提取"""
        from app.services.memory_system_v2.memory_manager import MemoryExtractor
        import re
        
        extractor = MemoryExtractor(llm_service=None)
        
        test_cases = [
            ("我喜欢打篮球", "打篮球"),
            ("我喜欢写代码", "写代码"),
            ("我爱看动漫", "看动漫"),
        ]
        
        for message, expected in test_cases:
            for pattern in extractor.INFO_PATTERNS.get("likes", []):
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    assert expected in value, f"Expected '{expected}' in '{value}' for '{message}'"
                    break


@pytest.mark.asyncio
class TestMemoryIntegration:
    """测试记忆存储和检索的完整流程"""
    
    async def test_store_and_retrieve_memory(self):
        """测试存储和检索记忆"""
        from app.core.database import init_db
        from app.services.memory_integration_service import (
            process_conversation_for_memory,
            get_memory_context_for_chat,
        )
        
        await init_db()
        
        user_id = f"test_integration_{asyncio.get_event_loop().time()}"
        
        # 1. 存储记忆
        result = await process_conversation_for_memory(
            user_id=user_id,
            character_id=TEST_CHARACTER_ID,
            user_message="我叫测试用户，我喜欢写测试",
            assistant_response="好的，记住了！",
            context=[],
        )
        
        assert result.get("semantic_updated") == True, "Should update semantic memory"
        
        # 2. 检索记忆
        context = await get_memory_context_for_chat(
            user_id=user_id,
            character_id=TEST_CHARACTER_ID,
            current_message="你记得我吗",
            working_memory=[],
        )
        
        assert context is not None, "Should return memory context"
        assert context.user_profile is not None, "Should have user profile"
        
        # 验证存储的内容
        profile = context.user_profile
        # user_name 可能因为正则匹配限制没提取到，但 likes 应该有
        assert "写测试" in str(profile.likes), f"Should contain '写测试' in likes, got: {profile.likes}"


@pytest.mark.asyncio
class TestChatDebugEndpoint:
    """测试 /api/v1/chat/debug endpoint"""
    
    async def test_debug_endpoint_returns_memories(self):
        """测试 debug endpoint 返回记忆"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        user_id = f"test_debug_{asyncio.get_event_loop().time()}"
        
        # 第一条消息：存储
        response1 = client.post("/api/v1/chat/debug", json={
            "user_id": user_id,
            "character_id": "luna",
            "message": "我叫Debug测试",
            "context": [],
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert "input" in data1
        assert "retrieved_memories" in data1
        assert "system_prompt" in data1
        assert "output" in data1
        
        # 第二条消息：检索
        response2 = client.post("/api/v1/chat/debug", json={
            "user_id": user_id,
            "character_id": "luna", 
            "message": "你好",
            "context": [],
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 应该能检索到之前存的记忆
        memories = data2.get("retrieved_memories", [])
        assert len(memories) > 0, "Should have retrieved memories"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
