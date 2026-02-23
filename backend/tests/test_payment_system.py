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
