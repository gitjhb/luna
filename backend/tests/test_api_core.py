"""
Core API Tests - 核心接口测试
=============================

保证基础接口稳定：
- 礼物系统
- 钱包系统  
- 亲密度系统
- 聊天系统
"""

import pytest
import httpx
from uuid import uuid4

BASE_URL = "http://localhost:8000/api/v1"

# 测试用户
TEST_USER_ID = "test-user-123"
TEST_CHARACTER_ID = "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f"


class TestGiftAPI:
    """礼物系统测试"""
    
    @pytest.mark.asyncio
    async def test_get_gift_catalog(self):
        """测试获取礼物目录"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/gifts/catalog")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            # 检查礼物字段
            gift = data[0]
            assert "gift_type" in gift
            assert "price" in gift
            assert "xp_reward" in gift
            assert "icon" in gift
    
    @pytest.mark.asyncio
    async def test_send_gift_success(self):
        """测试送礼物成功"""
        async with httpx.AsyncClient() as client:
            # 先确保有足够金币
            wallet_response = await client.get(f"{BASE_URL}/payment/wallet")
            assert wallet_response.status_code == 200
            
            # 送礼物
            idempotency_key = str(uuid4())
            response = await client.post(
                f"{BASE_URL}/gifts/send",
                json={
                    "character_id": TEST_CHARACTER_ID,
                    "gift_type": "rose",
                    "idempotency_key": idempotency_key,
                    "trigger_ai_response": False,  # 测试时不触发AI
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "gift_id" in data
            assert "new_balance" in data
            assert "xp_awarded" in data
    
    @pytest.mark.asyncio
    async def test_send_gift_idempotency(self):
        """测试礼物幂等性（重复请求不重复扣费）"""
        async with httpx.AsyncClient() as client:
            idempotency_key = str(uuid4())
            payload = {
                "character_id": TEST_CHARACTER_ID,
                "gift_type": "rose",
                "idempotency_key": idempotency_key,
                "trigger_ai_response": False,
            }
            
            # 第一次请求
            response1 = await client.post(f"{BASE_URL}/gifts/send", json=payload)
            assert response1.status_code == 200
            data1 = response1.json()
            balance1 = data1.get("new_balance")
            
            # 第二次请求（相同 idempotency_key）
            response2 = await client.post(f"{BASE_URL}/gifts/send", json=payload)
            assert response2.status_code == 200
            data2 = response2.json()
            
            # 应该标记为重复，不再扣费
            assert data2.get("is_duplicate") == True
    
    @pytest.mark.asyncio
    async def test_send_gift_invalid_type(self):
        """测试无效礼物类型"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/gifts/send",
                json={
                    "character_id": TEST_CHARACTER_ID,
                    "gift_type": "invalid_gift_type",
                    "idempotency_key": str(uuid4()),
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == False
            assert data["error"] == "invalid_gift_type"


class TestWalletAPI:
    """钱包系统测试"""
    
    @pytest.mark.asyncio
    async def test_get_wallet(self):
        """测试获取钱包余额"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/payment/wallet")
            assert response.status_code == 200
            data = response.json()
            assert "total_credits" in data
            assert "purchased_credits" in data
    
    @pytest.mark.asyncio
    async def test_get_transactions(self):
        """测试获取交易记录"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/wallet/transactions")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # 检查交易记录字段
            if len(data) > 0:
                tx = data[0]
                assert "transaction_id" in tx
                assert "transaction_type" in tx
                assert "amount" in tx
                assert "created_at" in tx
    
    @pytest.mark.asyncio
    async def test_purchase_credits(self):
        """测试购买金币"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/payment/purchase",
                json={
                    "package_id": "pack_60",
                    "payment_provider": "mock",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "credits_added" in data
            assert "wallet" in data


class TestIntimacyAPI:
    """亲密度系统测试"""
    
    @pytest.mark.asyncio
    async def test_get_intimacy(self):
        """测试获取亲密度"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/intimacy/{TEST_CHARACTER_ID}")
            assert response.status_code == 200
            data = response.json()
            assert "current_level" in data
            assert "total_xp" in data
            assert "intimacy_stage" in data
    
    @pytest.mark.asyncio
    async def test_award_xp(self):
        """测试奖励XP"""
        async with httpx.AsyncClient() as client:
            # Endpoint 格式: /intimacy/{character_id}/award/{action_type}
            response = await client.post(
                f"{BASE_URL}/intimacy/{TEST_CHARACTER_ID}/award/message"
            )
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "xp_awarded" in data


class TestChatAPI:
    """聊天系统测试"""
    
    @pytest.mark.asyncio
    async def test_get_characters(self):
        """测试获取角色列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/characters")
            assert response.status_code == 200
            data = response.json()
            # API 返回 {"characters": [...], "total": N} 格式
            assert "characters" in data
            assert isinstance(data["characters"], list)
            assert len(data["characters"]) > 0
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """测试创建聊天会话"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/chat/sessions",
                json={"character_id": TEST_CHARACTER_ID}
            )
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
    
    @pytest.mark.asyncio
    async def test_get_sessions(self):
        """测试获取会话列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/chat/sessions")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestHealthAPI:
    """健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def run_quick_tests():
        """快速运行关键测试"""
        print("🧪 Running quick API tests...\n")
        
        async with httpx.AsyncClient() as client:
            tests = [
                ("Health Check", "GET", "http://localhost:8000/health", None),
                ("Gift Catalog", "GET", f"{BASE_URL}/gifts/catalog", None),
                ("Wallet", "GET", f"{BASE_URL}/payment/wallet", None),
                ("Characters", "GET", f"{BASE_URL}/characters", None),
                ("Intimacy", "GET", f"{BASE_URL}/intimacy/{TEST_CHARACTER_ID}", None),
                ("Transactions", "GET", f"{BASE_URL}/wallet/transactions", None),
            ]
            
            for name, method, url, payload in tests:
                try:
                    if method == "GET":
                        response = await client.get(url)
                    else:
                        response = await client.post(url, json=payload)
                    
                    status = "✅" if response.status_code == 200 else "❌"
                    print(f"{status} {name}: {response.status_code}")
                except Exception as e:
                    print(f"❌ {name}: {e}")
            
            # 测试送礼物
            print("\n🎁 Testing Gift Send...")
            try:
                response = await client.post(
                    f"{BASE_URL}/gifts/send",
                    json={
                        "character_id": TEST_CHARACTER_ID,
                        "gift_type": "rose",
                        "idempotency_key": str(uuid4()),
                        "trigger_ai_response": False,
                    }
                )
                data = response.json()
                if response.status_code == 200 and data.get("success"):
                    print(f"✅ Gift Send: success, new_balance={data.get('new_balance')}")
                else:
                    print(f"❌ Gift Send: {data}")
            except Exception as e:
                print(f"❌ Gift Send: {e}")
        
        print("\n✨ Quick tests completed!")
    
    asyncio.run(run_quick_tests())
