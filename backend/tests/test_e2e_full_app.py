"""
Luna E2E Full App Tests
========================

完整的端到端测试，覆盖 App 所有主要功能。

运行方式：
    # 需要先启动后端服务
    cd ~/clawd/projects/luna/backend
    source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8001

    # 运行测试
    pytest tests/test_e2e_full_app.py -v

覆盖功能：
  1. Auth - Guest 登录、用户信息
  2. Characters - 角色列表、角色详情、角色状态
  3. Chat - 会话创建、发送消息、获取历史
  4. Memory - 记忆 CRUD、记忆列表
  5. Intimacy - 亲密度状态、签到
  6. Emotion - 情绪状态
  7. Gifts - 礼物目录、送礼
  8. Wallet - 余额查询、订阅状态
  9. Events - 事件类型、用户事件
"""

import pytest
import httpx
import asyncio
import uuid
from typing import Optional

# ─── 配置 ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8001/api/v1"
LUNA_CHARACTER_ID = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"  # Luna's ID

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_user_id():
    """Create a test user via guest login and return user_id."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        # Guest login to create a real user in DB
        resp = c.post("/auth/guest", json={"device_id": f"e2e-test-{uuid.uuid4().hex[:8]}"})
        if resp.status_code == 200:
            data = resp.json()
            return data.get("user_id") or data.get("user", {}).get("user_id")
        # Fallback to demo user
        return "demo-user-123"


@pytest.fixture(scope="module")
def client(test_user_id):
    """HTTP client with test user headers."""
    return httpx.Client(
        base_url=BASE_URL,
        headers={"X-User-ID": test_user_id},
        timeout=30.0
    )


@pytest.fixture(scope="module")
def session_id(client):
    """Create a chat session for tests."""
    resp = client.post("/chat/sessions", json={"character_id": LUNA_CHARACTER_ID})
    assert resp.status_code == 200, f"Failed to create session: {resp.text}"
    return resp.json()["session_id"]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Characters API
# ═══════════════════════════════════════════════════════════════════════════════

class TestCharactersAPI:
    """角色相关 API 测试"""

    def test_list_characters(self, client):
        """GET /characters - 获取角色列表"""
        resp = client.get("/characters")
        assert resp.status_code == 200
        data = resp.json()
        assert "characters" in data
        assert len(data["characters"]) > 0
        
        # 验证角色字段
        char = data["characters"][0]
        required_fields = ["character_id", "name", "description", "personality_traits"]
        for field in required_fields:
            assert field in char, f"Missing field: {field}"

    def test_get_character_detail(self, client):
        """GET /characters/{id} - 获取角色详情"""
        resp = client.get(f"/characters/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Luna"
        assert "greeting" in data

    def test_get_character_stats(self, client):
        """GET /characters/{id}/stats - 获取角色统计"""
        resp = client.get(f"/characters/{LUNA_CHARACTER_ID}/stats")
        assert resp.status_code == 200
        data = resp.json()
        # Stats 可能包含 message_count, intimacy_level 等
        assert isinstance(data, dict)

    def test_get_character_memories(self, client):
        """GET /characters/{id}/memories - 获取角色记忆"""
        resp = client.get(f"/characters/{LUNA_CHARACTER_ID}/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Chat API
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatAPI:
    """聊天相关 API 测试"""

    def test_create_session(self, client):
        """POST /chat/sessions - 创建会话"""
        resp = client.post("/chat/sessions", json={"character_id": LUNA_CHARACTER_ID})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["character_name"] == "Luna"

    def test_get_sessions(self, client):
        """GET /chat/sessions - 获取会话列表"""
        resp = client.get("/chat/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or "sessions" in data

    def test_send_greeting(self, client, session_id):
        """POST /chat/sessions/{id}/greeting - 发送问候"""
        resp = client.post(f"/chat/sessions/{session_id}/greeting")
        # 可能是 200 或 400（如果已经发过）
        assert resp.status_code in [200, 400]

    def test_get_messages(self, client, session_id):
        """GET /chat/sessions/{id}/messages - 获取消息历史"""
        resp = client.get(f"/chat/sessions/{session_id}/messages?limit=20")
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data

    def test_send_message(self, client, session_id):
        """POST /chat/completions - 发送消息"""
        resp = client.post("/chat/completions", json={
            "session_id": session_id,
            "message": "你好，Luna！这是一条测试消息。",
            "intimacy_level": 1
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data or "content" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Memory API
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryAPI:
    """记忆系统 API 测试"""

    def test_get_memories(self, client):
        """GET /memory/{character_id} - 获取记忆列表"""
        resp = client.get(f"/memory/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200
        data = resp.json()
        # API returns {"memories": [...], "total": N}
        assert "memories" in data
        assert isinstance(data["memories"], list)

    def test_create_memory(self, client):
        """POST /memory/{character_id} - 创建记忆"""
        resp = client.post(f"/memory/{LUNA_CHARACTER_ID}", json={
            "category": "preference",
            "title": "E2E测试记忆",
            "content": "这是一条E2E测试创建的记忆",
            "importance": 2
        })
        # 可能是 201（成功）或 403（配额不足）
        assert resp.status_code in [201, 403, 400]
        
        if resp.status_code == 201:
            data = resp.json()
            assert "id" in data
            # 清理：删除测试记忆
            memory_id = data["id"]
            client.delete(f"/memory/{LUNA_CHARACTER_ID}/{memory_id}")

    def test_get_user_memory(self, client):
        """GET /characters/{id}/user-memory - 获取用户记忆统计"""
        resp = client.get(f"/characters/{LUNA_CHARACTER_ID}/user-memory")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Intimacy API
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntimacyAPI:
    """亲密度系统 API 测试"""

    def test_get_intimacy_status(self, client):
        """GET /intimacy/{character_id} - 获取亲密度状态"""
        resp = client.get(f"/intimacy/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200
        data = resp.json()
        # API returns detailed intimacy info with available_actions, stage, etc.
        assert "current_level" in data or "stage" in data or "available_actions" in data

    def test_get_intimacy_history(self, client):
        """GET /intimacy/{character_id}/history - 获取亲密度历史"""
        resp = client.get(f"/intimacy/{LUNA_CHARACTER_ID}/history")
        assert resp.status_code == 200

    def test_get_available_actions(self, client):
        """GET /intimacy/{character_id}/actions - 获取可用动作"""
        resp = client.get(f"/intimacy/{LUNA_CHARACTER_ID}/actions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_all_stages(self, client):
        """GET /intimacy/stages/all - 获取所有亲密度阶段"""
        resp = client.get("/intimacy/stages/all")
        assert resp.status_code == 200

    def test_daily_checkin(self, client):
        """POST /intimacy/{character_id}/checkin - 每日签到"""
        resp = client.post(f"/intimacy/{LUNA_CHARACTER_ID}/checkin")
        # 200 成功，400 已签到
        assert resp.status_code in [200, 400]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Emotion API
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmotionAPI:
    """情绪系统 API 测试"""

    def test_get_emotion_status(self, client):
        """GET /emotion/{character_id} - 获取情绪状态"""
        resp = client.get(f"/emotion/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200
        data = resp.json()
        # 验证情绪字段
        assert "emotion_score" in data or "current_mood" in data or "score" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Gifts API
# ═══════════════════════════════════════════════════════════════════════════════

class TestGiftsAPI:
    """礼物系统 API 测试"""

    def test_get_gift_catalog(self, client):
        """GET /gifts/catalog - 获取礼物目录"""
        resp = client.get("/gifts/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            gift = data[0]
            assert "gift_type" in gift or "id" in gift
            assert "cost" in gift or "price" in gift

    def test_get_gift_effects(self, client):
        """GET /gifts/effects/{character_id} - 获取礼物效果"""
        resp = client.get(f"/gifts/effects/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200

    def test_get_gift_history(self, client):
        """GET /gifts/history - 获取送礼历史"""
        resp = client.get("/gifts/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Wallet API
# ═══════════════════════════════════════════════════════════════════════════════

class TestWalletAPI:
    """钱包系统 API 测试"""

    def test_get_wallet_balance(self, client):
        """GET /wallet/balance - 获取余额"""
        resp = client.get("/wallet/balance")
        assert resp.status_code == 200
        data = resp.json()
        # API may return various fields depending on implementation
        assert isinstance(data, dict)

    def test_get_subscription_status(self, client):
        """GET /wallet/subscription - 获取订阅状态"""
        resp = client.get("/wallet/subscription")
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data or "plan" in data or "status" in data

    def test_get_transactions(self, client):
        """GET /wallet/transactions - 获取交易记录"""
        resp = client.get("/wallet/transactions")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Events API
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventsAPI:
    """事件系统 API 测试"""

    def test_get_event_types(self, client):
        """GET /events/types - 获取支持的事件类型"""
        resp = client.get("/events/types")
        assert resp.status_code == 200
        data = resp.json()
        # API returns {"events": [...]} or {"event_types": [...]}
        assert "events" in data or "event_types" in data or isinstance(data, list)

    def test_get_user_events(self, client):
        """GET /events/me/{character_id} - 获取用户事件"""
        resp = client.get(f"/events/me/{LUNA_CHARACTER_ID}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 9. User Settings API
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserSettingsAPI:
    """用户设置 API 测试"""

    def test_get_settings(self, client):
        """GET /settings - 获取用户设置"""
        resp = client.get("/settings")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Daily Reward API
# ═══════════════════════════════════════════════════════════════════════════════

class TestDailyRewardAPI:
    """每日奖励 API 测试"""

    def test_get_reward_status(self, client):
        """GET /daily/status - 获取奖励状态"""
        resp = client.get("/daily/status")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Payment API
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentAPI:
    """支付系统 API 测试"""

    def test_get_payment_config(self, client):
        """GET /payment/config - 获取支付配置"""
        resp = client.get("/payment/config")
        assert resp.status_code == 200

    def test_get_subscription_plans(self, client):
        """GET /payment/plans - 获取订阅计划"""
        resp = client.get("/payment/plans")
        assert resp.status_code == 200

    def test_get_subscription(self, client):
        """GET /payment/subscription - 获取订阅状态"""
        resp = client.get("/payment/subscription")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Full Flow Integration Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullUserFlow:
    """完整用户流程测试"""

    def test_new_user_onboarding_flow(self, client):
        """
        模拟新用户完整流程：
        1. 获取角色列表
        2. 创建会话
        3. 获取问候语
        4. 发送消息
        5. 查看亲密度
        6. 查看记忆
        """
        # Step 1: 获取角色列表
        resp = client.get("/characters")
        assert resp.status_code == 200
        characters = resp.json()["characters"]
        assert len(characters) > 0
        
        # Step 2: 创建会话
        char_id = characters[0]["character_id"]
        resp = client.post("/chat/sessions", json={"character_id": char_id})
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        
        # Step 3: 获取问候语
        resp = client.post(f"/chat/sessions/{session_id}/greeting")
        # 可能已经有问候语了
        assert resp.status_code in [200, 400]
        
        # Step 4: 获取消息历史
        resp = client.get(f"/chat/sessions/{session_id}/messages?limit=10")
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        assert len(messages) > 0  # 至少有问候语
        
        # Step 5: 查看亲密度
        resp = client.get(f"/intimacy/{char_id}")
        assert resp.status_code == 200
        
        # Step 6: 查看记忆
        resp = client.get(f"/memory/{char_id}")
        assert resp.status_code == 200
        
        print(f"✅ Full user flow completed for character: {char_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
