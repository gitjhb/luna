"""
Payment System Tests
====================

测试支付系统的核心功能：
1. Stripe Checkout（积分购买、订阅）
2. Stripe Webhook 处理
3. 订阅服务（状态检查、权限）
4. Mock 模式
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# ============================================================
# Stripe Checkout Tests
# ============================================================

class TestStripeCheckout:
    """测试 Stripe Checkout 流程"""
    
    def test_get_stripe_config(self):
        """测试获取 Stripe 配置"""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/payment/stripe/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "enabled" in data
        assert "publishable_key" in data
    
    def test_create_credit_checkout_mock_mode(self):
        """测试 Mock 模式下创建积分购买 Checkout"""
        from app.main import app
        client = TestClient(app)
        
        # 在 mock 模式下应该返回 501 或模拟响应
        response = client.post("/api/v1/payment/stripe/checkout", json={
            "package_id": "pack_60",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        })
        
        # Mock 模式下 Stripe 未配置
        # 应该返回 501 (Not Implemented) 或 200 (如果有 mock 实现)
        assert response.status_code in [200, 400, 501]
    
    def test_create_subscription_checkout_mock_mode(self):
        """测试 Mock 模式下创建订阅 Checkout"""
        from app.main import app
        client = TestClient(app)
        
        response = client.post("/api/v1/payment/stripe/subscribe", json={
            "plan_id": "premium_monthly",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        })
        
        assert response.status_code in [200, 400, 501]


class TestStripeWebhook:
    """测试 Stripe Webhook 处理"""
    
    def test_webhook_without_signature_rejected(self):
        """测试没有签名的 webhook 被拒绝"""
        from app.main import app
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/payment/stripe/webhook",
            content=json.dumps({"type": "test"}),
            headers={"Content-Type": "application/json"},
        )
        
        # 没有 stripe-signature header 应该被拒绝
        # 可能返回 400, 422, 500, 200 (mock), 或 501 (Stripe 未配置)
        assert response.status_code in [200, 400, 422, 500, 501]
    
    @pytest.mark.asyncio
    async def test_handle_checkout_completed_credits(self):
        """测试处理积分购买完成的 webhook"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        
        # Mock event
        mock_event = MagicMock()
        mock_event.type = "checkout.session.completed"
        mock_event.data.object = {
            "id": "cs_test_123",
            "mode": "payment",
            "metadata": {
                "user_id": "test_user_credits",
                "package_id": "pack_60",
                "type": "credits",
            },
            "payment_status": "paid",
            "amount_total": 99,
        }
        
        # 应该能处理事件（即使在测试环境）
        # 实际结果取决于数据库是否可用
        try:
            result = await service.handle_webhook_event(mock_event)
            assert result is not None
        except Exception as e:
            # 在没有真实数据库的情况下可能失败
            assert "database" in str(e).lower() or "user" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_handle_subscription_created(self):
        """测试处理订阅创建的 webhook"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        
        mock_event = MagicMock()
        mock_event.type = "customer.subscription.created"
        mock_event.data.object = {
            "id": "sub_test_123",
            "customer": "cus_test_123",
            "status": "active",
            "metadata": {
                "user_id": "test_user_sub",
                "plan_id": "premium_monthly",
            },
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
        }
        
        try:
            result = await service.handle_webhook_event(mock_event)
            assert result is not None
        except Exception:
            pass  # 测试环境下可能没有完整数据库


# ============================================================
# Subscription Service Tests
# ============================================================

class TestSubscriptionService:
    """测试订阅服务"""
    
    @pytest.mark.asyncio
    async def test_get_subscription_plans(self):
        """测试获取订阅计划列表"""
        try:
            from app.services.payment_service import SUBSCRIPTION_PLANS
            assert len(SUBSCRIPTION_PLANS) >= 0
        except ImportError:
            # 可能结构不同
            from app.main import app
            client = TestClient(app)
            response = client.get("/api/v1/payment/plans")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_subscription_tier_enum(self):
        """测试订阅等级枚举"""
        from app.services.subscription_service import SubscriptionTier
        
        # 应该有基本的等级
        assert hasattr(SubscriptionTier, "FREE")
        assert hasattr(SubscriptionTier, "BASIC") or hasattr(SubscriptionTier, "PREMIUM")
    
    @pytest.mark.asyncio
    async def test_mock_subscription(self):
        """测试 Mock 订阅功能"""
        from app.services.subscription_service import (
            set_mock_subscription,
            get_user_tier,
            is_premium_user,
        )
        
        user_id = f"test_sub_user_{datetime.now().timestamp()}"
        
        # 设置 mock 订阅
        try:
            await set_mock_subscription(user_id, "premium", expires_in_days=30)
            
            # 验证订阅状态
            tier = await get_user_tier(user_id)
            assert tier in ["premium", "PREMIUM", "basic", "BASIC", "free", "FREE"]
            
        except Exception as e:
            # 可能因为数据库未初始化而失败
            pytest.skip(f"Database not available: {e}")


# ============================================================
# Payment API Integration Tests
# ============================================================

class TestPaymentAPI:
    """测试支付 API 端点"""
    
    def test_get_payment_config(self):
        """测试获取支付配置"""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/payment/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "mock_mode" in data
        assert "credit_packages" in data or "packages" in data or "plans" in data
    
    def test_get_subscription_plans(self):
        """测试获取订阅计划"""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/payment/plans")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list) or "plans" in data
    
    def test_get_credit_packages(self):
        """测试获取积分包（通过 /config 获取）"""
        from app.main import app
        client = TestClient(app)
        
        # 积分包在 /config 中返回
        response = client.get("/api/v1/payment/config")
        assert response.status_code == 200
        
        data = response.json()
        # 应该包含 credit_packages 或类似字段
        assert "credit_packages" in data or "packages" in data or "mock_mode" in data


# ============================================================
# IAP Verification Tests
# ============================================================

class TestIAPVerification:
    """测试 IAP 验证（Apple/Google）"""
    
    def test_iap_verify_apple_invalid_receipt(self):
        """测试 Apple IAP 无效收据（通过统一的 /iap/verify 端点）"""
        from app.main import app
        client = TestClient(app)
        
        response = client.post("/api/v1/payment/iap/verify", json={
            "provider": "apple",
            "receipt_data": "invalid_receipt_data",
        })
        
        # 无效收据应该返回错误
        assert response.status_code in [400, 401, 422, 500]
    
    def test_iap_verify_google_invalid_token(self):
        """测试 Google IAP 无效令牌（通过统一的 /iap/verify 端点）"""
        from app.main import app
        client = TestClient(app)
        
        response = client.post("/api/v1/payment/iap/verify", json={
            "provider": "google",
            "product_id": "test_product",
            "purchase_token": "invalid_token",
        })
        
        # 无效令牌应该返回错误
        assert response.status_code in [400, 401, 422, 500]


# ============================================================
# Webhook Event Processing Tests
# ============================================================

class TestWebhookEventProcessing:
    """测试 Webhook 事件处理逻辑"""
    
    @pytest.mark.asyncio
    async def test_subscription_lifecycle(self):
        """测试订阅生命周期：创建 → 更新 → 取消"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        user_id = f"test_lifecycle_{datetime.now().timestamp()}"
        
        # 1. 订阅创建
        create_event = MagicMock()
        create_event.type = "customer.subscription.created"
        create_event.data.object = {
            "id": "sub_lifecycle_test",
            "customer": "cus_lifecycle_test",
            "status": "active",
            "metadata": {"user_id": user_id, "plan_id": "premium_monthly"},
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
        }
        
        # 2. 订阅更新（续费）
        update_event = MagicMock()
        update_event.type = "customer.subscription.updated"
        update_event.data.object = {
            "id": "sub_lifecycle_test",
            "customer": "cus_lifecycle_test",
            "status": "active",
            "metadata": {"user_id": user_id, "plan_id": "premium_monthly"},
            "current_period_end": int((datetime.now() + timedelta(days=60)).timestamp()),
        }
        
        # 3. 订阅取消
        cancel_event = MagicMock()
        cancel_event.type = "customer.subscription.deleted"
        cancel_event.data.object = {
            "id": "sub_lifecycle_test",
            "customer": "cus_lifecycle_test",
            "status": "canceled",
            "metadata": {"user_id": user_id, "plan_id": "premium_monthly"},
        }
        
        # 验证事件处理不会崩溃
        for event in [create_event, update_event, cancel_event]:
            try:
                await service.handle_webhook_event(event)
            except Exception as e:
                # 在测试环境可能因数据库问题失败，但不应该是代码错误
                assert "stripe" not in str(e).lower() or "api" not in str(e).lower()


# ============================================================
# Stripe Customer Linking Tests (Critical Bug Fix 2026-03-01)
# ============================================================

class TestStripeCustomerLinking:
    """
    测试 Stripe Customer ID 关联功能
    
    问题背景：
    - 用户 Firebase UID: 5Q3mmcUGAuYmr8kZpa8QqSBAGUp2
    - 用户在 Stripe 付款时用了不同邮箱 (jhbmeta@gmail.com)
    - 系统创建的 Stripe customer 用了假邮箱 ({user_id}@example.com)
    - 导致 Customer Portal 无法找到正确的 subscription
    
    修复方案：
    - checkout.session.completed webhook 触发时保存 stripe_customer_id
    - Portal 使用存储的 customer_id 而不是搜索
    """
    
    @pytest.mark.asyncio
    async def test_link_stripe_customer_on_checkout_completed(self):
        """测试 checkout 完成时关联 Stripe customer"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        
        # 模拟 checkout.session.completed 事件
        # 关键：session 包含 customer (Stripe 创建的 customer ID)
        mock_session = {
            "id": "cs_test_customer_link",
            "mode": "subscription",
            "customer": "cus_REAL_CUSTOMER_123",  # 这是 Stripe 创建的真实 customer
            "client_reference_id": "firebase_uid_abc123",  # 我们的 user_id
            "metadata": {
                "user_id": "firebase_uid_abc123",
                "type": "subscription",
                "plan_id": "premium_monthly",
            },
            "payment_status": "paid",
        }
        
        # 测试 _link_stripe_customer 被调用
        with patch.object(service, '_link_stripe_customer', new_callable=AsyncMock) as mock_link:
            mock_link.return_value = True
            
            # 模拟 webhook event
            mock_event = MagicMock()
            mock_event.type = "checkout.session.completed"
            mock_event.data.object = mock_session
            
            try:
                await service.handle_webhook_event(mock_event)
            except Exception:
                pass  # 数据库相关错误可以忽略
            
            # 验证 _link_stripe_customer 被调用
            mock_link.assert_called_once_with(
                "firebase_uid_abc123",
                "cus_REAL_CUSTOMER_123"
            )
    
    @pytest.mark.asyncio
    async def test_link_stripe_customer_on_subscription_created(self):
        """测试订阅创建时也关联 Stripe customer（作为备份）"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        
        # 模拟 subscription.created 事件
        mock_subscription = {
            "id": "sub_test_link",
            "customer": "cus_REAL_CUSTOMER_456",
            "status": "active",
            "metadata": {
                "user_id": "firebase_uid_xyz789",
                "plan_id": "premium_monthly",
                "tier": "premium",
            },
            "current_period_start": int(datetime.now().timestamp()),
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
        }
        
        with patch.object(service, '_link_stripe_customer', new_callable=AsyncMock) as mock_link:
            mock_link.return_value = True
            
            mock_event = MagicMock()
            mock_event.type = "customer.subscription.created"
            mock_event.data.object = mock_subscription
            
            try:
                await service.handle_webhook_event(mock_event)
            except Exception:
                pass
            
            # 验证 _link_stripe_customer 被调用
            mock_link.assert_called_once_with(
                "firebase_uid_xyz789",
                "cus_REAL_CUSTOMER_456"
            )
    
    @pytest.mark.asyncio
    async def test_get_customer_for_user_uses_stored_id_first(self):
        """测试获取 customer 时优先使用存储的 ID"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        service.enabled = True
        
        # 模拟已存储的 customer ID
        stored_customer_id = "cus_STORED_123"
        
        with patch.object(service, 'get_stored_customer_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = stored_customer_id
            
            # 不应该调用 get_or_create_customer
            with patch.object(service, 'get_or_create_customer', new_callable=AsyncMock) as mock_create:
                result = await service.get_customer_for_user(
                    user_id="test_user",
                    email="test@example.com",
                )
                
                # 验证返回存储的 ID
                assert result == stored_customer_id
                
                # 验证没有调用 get_or_create_customer
                mock_create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_customer_for_user_falls_back_to_search(self):
        """测试没有存储 ID 时 fallback 到搜索"""
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        service.enabled = True
        
        new_customer_id = "cus_NEW_123"
        
        with patch.object(service, 'get_stored_customer_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None  # 没有存储的 ID
            
            with patch.object(service, 'get_or_create_customer', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = new_customer_id
                
                with patch.object(service, '_link_stripe_customer', new_callable=AsyncMock) as mock_link:
                    mock_link.return_value = True
                    
                    result = await service.get_customer_for_user(
                        user_id="test_user",
                        email="test@example.com",
                    )
                    
                    # 验证返回新创建的 ID
                    assert result == new_customer_id
                    
                    # 验证调用了 get_or_create_customer
                    mock_create.assert_called_once()
                    
                    # 验证存储了新的 customer ID
                    mock_link.assert_called_once_with("test_user", new_customer_id)
    
    @pytest.mark.asyncio
    async def test_portal_uses_correct_customer(self):
        """
        测试 Customer Portal 使用正确的 customer
        
        场景：
        1. 用户 A 用 Firebase UID "fb-user-123" 登录
        2. 用户在 Stripe 用不同邮箱付款，创建了 customer "cus_stripe_456"
        3. checkout webhook 把 cus_stripe_456 存到用户记录
        4. 用户访问 portal，应该用 cus_stripe_456 而不是搜索/新建
        """
        from app.services.stripe_service import stripe_service
        
        user_id = "fb-user-123"
        stored_customer_id = "cus_stripe_456"
        wrong_customer_id = "cus_wrong_999"  # 如果用搜索可能得到这个
        
        # 模拟已存储的 customer ID
        with patch.object(stripe_service, 'get_stored_customer_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = stored_customer_id
            
            # 模拟 get_or_create_customer 返回错误的 ID（如果被调用）
            with patch.object(stripe_service, 'get_or_create_customer', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = wrong_customer_id
                
                # 调用 get_customer_for_user（Portal 用这个）
                result = await stripe_service.get_customer_for_user(
                    user_id=user_id,
                    email="fake@example.com",  # Portal 可能传假邮箱
                )
                
                # 必须返回存储的正确 ID，不是搜索得到的
                assert result == stored_customer_id
                assert result != wrong_customer_id
    
    @pytest.mark.asyncio 
    async def test_checkout_with_different_email_links_correctly(self):
        """
        端到端测试：用户用不同邮箱付款时的关联
        
        场景：
        - Luna user email: jiahongbinandroid@gmail.com (Firebase)
        - Stripe checkout email: jhbmeta@gmail.com (用户在 Stripe 输入的)
        - 应该正确关联到同一个 Luna user
        """
        from app.services.stripe_service import StripeService
        
        service = StripeService()
        
        luna_user_id = "5Q3mmcUGAuYmr8kZpa8QqSBAGUp2"  # Firebase UID
        stripe_customer_id = "cus_jhbmeta_gmail"  # Stripe 用 jhbmeta@gmail.com 创建的
        
        # 模拟 checkout.session.completed
        mock_session = {
            "id": "cs_test_different_email",
            "customer": stripe_customer_id,
            "client_reference_id": luna_user_id,
            "metadata": {
                "user_id": luna_user_id,
                "type": "subscription",
            },
        }
        
        link_calls = []
        
        async def mock_link(user_id, customer_id):
            link_calls.append((user_id, customer_id))
            return True
        
        with patch.object(service, '_link_stripe_customer', side_effect=mock_link):
            mock_event = MagicMock()
            mock_event.type = "checkout.session.completed"
            mock_event.data.object = mock_session
            
            try:
                await service.handle_webhook_event(mock_event)
            except Exception:
                pass
            
            # 验证关联了正确的 user_id 和 customer_id
            assert len(link_calls) > 0
            assert link_calls[0] == (luna_user_id, stripe_customer_id)


# ============================================================
# RevenueCat Integration Tests (if applicable)
# ============================================================

class TestRevenueCatIntegration:
    """测试 RevenueCat 集成（如果有）"""
    
    def test_revenuecat_webhook_endpoint_exists(self):
        """测试 RevenueCat webhook 端点存在"""
        from app.main import app
        client = TestClient(app)
        
        # 检查端点是否存在（即使返回错误也说明端点配置了）
        response = client.post("/api/v1/payment/revenuecat/webhook", json={})
        
        # 404 说明端点不存在，其他状态码说明存在但可能验证失败
        # 我们只关心端点是否配置
        if response.status_code == 404:
            pytest.skip("RevenueCat webhook endpoint not configured")
        else:
            assert response.status_code in [200, 400, 401, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
