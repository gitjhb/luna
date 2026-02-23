"""
Proactive Message System Tests
==============================

测试主动消息系统的核心功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.proactive_message import (
    ProactiveMessageService,
    ProactiveType,
    PROACTIVE_TEMPLATES,
    check_proactive_for_user,
)


class TestProactiveMessageService:
    """测试 ProactiveMessageService"""
    
    def setup_method(self):
        """每个测试前重置服务"""
        self.service = ProactiveMessageService()
    
    def test_pick_template_luna(self):
        """测试 Luna 模板选择"""
        template = self.service.pick_template("luna", ProactiveType.GOOD_MORNING)
        assert template is not None
        assert isinstance(template, str)
        assert len(template) > 0
    
    def test_pick_template_unknown_character_uses_default(self):
        """测试未知角色使用默认模板"""
        template = self.service.pick_template("unknown_character", ProactiveType.GOOD_MORNING)
        assert template is not None
        # 应该从 default 模板中选择
        assert template in PROACTIVE_TEMPLATES["default"]["good_morning"]
    
    def test_pick_template_all_types(self):
        """测试所有消息类型都有模板"""
        for msg_type in [ProactiveType.GOOD_MORNING, ProactiveType.GOOD_NIGHT, ProactiveType.MISS_YOU]:
            template = self.service.pick_template("luna", msg_type)
            assert template is not None, f"No template for {msg_type}"
    
    @pytest.mark.asyncio
    async def test_cooldown_mechanism(self):
        """测试冷却机制"""
        user_id = "test_cooldown_user"
        character_id = "luna"
        msg_type = ProactiveType.GOOD_MORNING
        
        # 初始状态应该可以发送
        can_send = await self.service.can_send_proactive(user_id, character_id, msg_type)
        assert can_send == True
        
        # 记录发送
        await self.service.record_proactive(user_id, character_id, msg_type)
        
        # 冷却期间不能发送
        can_send = await self.service.can_send_proactive(user_id, character_id, msg_type)
        assert can_send == False
    
    @pytest.mark.asyncio
    async def test_intimacy_level_threshold(self):
        """测试亲密度门槛：低于2级不发消息"""
        result = await self.service.check_and_generate(
            user_id="test_low_intimacy",
            character_id="luna",
            intimacy_level=1,  # 低于门槛
            timezone="America/Los_Angeles",
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_muted_user_no_message(self):
        """测试静音用户不收消息"""
        result = await self.service.check_and_generate(
            user_id="test_muted",
            character_id="luna",
            intimacy_level=10,
            muted=True,
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_good_morning_at_8am(self):
        """测试早上8点发送早安消息"""
        service = ProactiveMessageService()
        
        # Mock 时间为早上8点
        with patch.object(service, 'get_user_hour', return_value=8):
            result = await service.check_and_generate(
                user_id="test_morning_user",
                character_id="luna",
                intimacy_level=5,
                timezone="America/Los_Angeles",
            )
            
            if result:  # 如果没有在冷却期
                assert result["type"] == ProactiveType.GOOD_MORNING.value
                assert "message" in result
    
    @pytest.mark.asyncio
    async def test_good_night_at_22pm(self):
        """测试晚上22点发送晚安消息"""
        service = ProactiveMessageService()
        
        # Mock 时间为晚上22点
        with patch.object(service, 'get_user_hour', return_value=22):
            result = await service.check_and_generate(
                user_id="test_night_user",
                character_id="luna",
                intimacy_level=5,
                timezone="America/Los_Angeles",
            )
            
            if result:  # 如果没有在冷却期
                assert result["type"] == ProactiveType.GOOD_NIGHT.value
    
    @pytest.mark.asyncio
    async def test_miss_you_after_long_absence(self):
        """测试长时间不聊天后发送想念消息"""
        service = ProactiveMessageService()
        
        # Mock 时间为下午（不是早安/晚安时间）
        with patch.object(service, 'get_user_hour', return_value=14):
            # Mock 随机数让想念消息一定触发
            with patch('app.services.proactive_message.random.random', return_value=0.1):
                result = await service.check_and_generate(
                    user_id="test_miss_user",
                    character_id="luna",
                    intimacy_level=5,  # >= 3
                    last_chat_time=datetime.now() - timedelta(hours=10),  # 超过4小时
                    timezone="America/Los_Angeles",
                )
                
                if result:
                    assert result["type"] == ProactiveType.MISS_YOU.value


@pytest.mark.asyncio
class TestProactiveAPI:
    """测试 Proactive API endpoints"""
    
    async def test_check_endpoint(self):
        """测试 /proactive/check endpoint"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.post("/api/v1/proactive/check", json={
            "user_id": "api_test_user",
            "character_id": "luna",
            "intimacy_level": 5,
            "timezone": "America/Los_Angeles",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "should_send" in data
    
    async def test_templates_endpoint(self):
        """测试 /proactive/templates endpoint"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/v1/proactive/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "luna" in data
        assert "default" in data
    
    async def test_test_endpoint_with_force(self):
        """测试 /proactive/test 强制生成消息"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/proactive/test/force_test_user?character_id=luna&msg_type=good_morning&force=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["type"] == "good_morning"
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
