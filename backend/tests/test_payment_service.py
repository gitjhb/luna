"""
Tests for Payment Service
=========================

Covers:
- Subscription management (create, update, cancel)
- Credit purchases and wallet operations
- Webhook processing
- Payment plan validation
- Mock payment processing
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Dict, Any

# Import the service we're testing
from app.services.payment_service import (
    PaymentService,
    SUBSCRIPTION_PLANS,
    CREDIT_PACKAGES,
    TIER_HIERARCHY
)


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for PaymentService"""
    with patch('app.services.payment_service.MOCK_PAYMENT', True):
        # Clear mock storage before each test
        from app.services.payment_service import _subscriptions, _wallets, _transactions
        _subscriptions.clear()
        _wallets.clear()
        _transactions.clear()
        yield


@pytest.fixture
def payment_service(mock_dependencies):
    """Create PaymentService instance with mocked dependencies"""
    return PaymentService()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return str(uuid4())


class TestPaymentService:
    """Test cases for PaymentService"""

    @pytest.mark.asyncio
    async def test_create_subscription_premium_plan(self, payment_service, sample_user_id):
        """
        Test creating a premium subscription.
        
        Should:
        - Create subscription record
        - Set correct tier and features
        - Calculate expiration date
        """
        # Act
        result = await payment_service.create_subscription(
            user_id=sample_user_id,
            plan_id="premium",
            billing_cycle="monthly"
        )
        
        # Assert
        assert result['success'] is True
        assert result['subscription']['plan_id'] == "premium"
        assert result['subscription']['tier'] == "premium"
        assert result['subscription']['status'] == "active"
        assert 'subscription_id' in result['subscription']
        
        # Verify subscription exists in storage
        subscription = await payment_service.get_subscription(sample_user_id)
        assert subscription is not None
        assert subscription['tier'] == "premium"

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_plan(self, payment_service, sample_user_id):
        """
        Test creating subscription with invalid plan ID.
        
        Should reject with appropriate error message.
        """
        # Act
        result = await payment_service.create_subscription(
            user_id=sample_user_id,
            plan_id="invalid_plan",
            billing_cycle="monthly"
        )
        
        # Assert
        assert result['success'] is False
        assert 'invalid plan' in result['error'].lower() or \
               'plan not found' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_upgrade_subscription(self, payment_service, sample_user_id):
        """
        Test upgrading from premium to VIP subscription.
        
        Should:
        - Update existing subscription
        - Preserve remaining time with prorating
        - Update tier and benefits
        """
        # Create initial premium subscription
        await payment_service.create_subscription(
            user_id=sample_user_id,
            plan_id="premium", 
            billing_cycle="monthly"
        )
        
        # Upgrade to VIP
        result = await payment_service.upgrade_subscription(
            user_id=sample_user_id,
            new_plan_id="vip"
        )
        
        # Assert
        assert result['success'] is True
        assert result['subscription']['plan_id'] == "vip"
        assert result['subscription']['tier'] == "vip"
        
        # Verify tier hierarchy upgrade
        subscription = await payment_service.get_subscription(sample_user_id)
        assert subscription['tier'] == "vip"

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, payment_service, sample_user_id):
        """
        Test canceling active subscription.
        
        Should:
        - Set status to canceled
        - Preserve access until expiration
        - Record cancellation timestamp
        """
        # Create subscription first
        await payment_service.create_subscription(
            user_id=sample_user_id,
            plan_id="premium",
            billing_cycle="monthly"
        )
        
        # Cancel subscription
        result = await payment_service.cancel_subscription(sample_user_id)
        
        # Assert
        assert result['success'] is True
        assert 'cancellation confirmed' in result['message'].lower()
        
        # Verify subscription is marked as canceled
        subscription = await payment_service.get_subscription(sample_user_id)
        assert subscription['status'] == "canceled"

    @pytest.mark.asyncio
    async def test_purchase_credits_valid_package(self, payment_service, sample_user_id):
        """
        Test purchasing credits with valid package.
        
        Should:
        - Add credits to user wallet
        - Apply bonus credits if applicable
        - Record transaction
        """
        # Act
        result = await payment_service.purchase_credits(
            user_id=sample_user_id,
            package_id="pack_300"  # 300 credits + 30 bonus = 330 total
        )
        
        # Assert
        assert result['success'] is True
        assert result['credits_added'] == 330  # 300 + 30 bonus
        assert result['transaction']['amount'] == 4.99
        
        # Verify wallet balance
        wallet = await payment_service.get_wallet_balance(sample_user_id)
        assert wallet['credits'] == 330

    @pytest.mark.asyncio
    async def test_purchase_credits_invalid_package(self, payment_service, sample_user_id):
        """
        Test purchasing credits with invalid package ID.
        
        Should reject with appropriate error.
        """
        # Act
        result = await payment_service.purchase_credits(
            user_id=sample_user_id,
            package_id="invalid_package"
        )
        
        # Assert
        assert result['success'] is False
        assert 'invalid package' in result['error'].lower() or \
               'package not found' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_spend_credits_sufficient_balance(self, payment_service, sample_user_id):
        """
        Test spending credits when user has sufficient balance.
        
        Should deduct credits and return success.
        """
        # Add credits first
        await payment_service.purchase_credits(sample_user_id, "pack_300")
        
        # Spend some credits
        result = await payment_service.spend_credits(sample_user_id, 100)
        
        # Assert
        assert result['success'] is True
        assert result['remaining_balance'] == 230  # 330 - 100
        
        # Verify wallet balance
        wallet = await payment_service.get_wallet_balance(sample_user_id)
        assert wallet['credits'] == 230

    @pytest.mark.asyncio
    async def test_spend_credits_insufficient_balance(self, payment_service, sample_user_id):
        """
        Test spending credits when user has insufficient balance.
        
        Should fail and preserve existing balance.
        """
        # Add small amount of credits
        await payment_service.purchase_credits(sample_user_id, "pack_60")  # 60 credits
        
        # Try to spend more than available
        result = await payment_service.spend_credits(sample_user_id, 100)
        
        # Assert
        assert result['success'] is False
        assert 'insufficient' in result['error'].lower()
        
        # Balance should remain unchanged
        wallet = await payment_service.get_wallet_balance(sample_user_id)
        assert wallet['credits'] == 60

    @pytest.mark.asyncio
    async def test_process_webhook_subscription_created(self, payment_service):
        """
        Test processing Stripe webhook for subscription creation.
        
        Should create new subscription in system.
        """
        # Mock webhook data
        webhook_data = {
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': 'cus_test456',
                    'status': 'active',
                    'items': {
                        'data': [{
                            'price': {
                                'id': 'price_premium_monthly'
                            }
                        }]
                    },
                    'current_period_end': int((datetime.now() + timedelta(days=30)).timestamp())
                }
            }
        }
        
        # Act
        result = await payment_service.process_webhook(webhook_data)
        
        # Assert
        assert result['success'] is True
        assert 'processed' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_process_webhook_subscription_canceled(self, payment_service, sample_user_id):
        """
        Test processing webhook for subscription cancellation.
        
        Should update subscription status to canceled.
        """
        # Create subscription first
        await payment_service.create_subscription(
            sample_user_id, "premium", "monthly"
        )
        
        # Mock webhook data
        webhook_data = {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': 'cus_test456',
                    'status': 'canceled'
                }
            }
        }
        
        # Act
        result = await payment_service.process_webhook(webhook_data)
        
        # Assert
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_check_subscription_status_expired(self, payment_service, sample_user_id):
        """
        Test checking subscription status for expired subscription.
        
        Should detect expiration and update status.
        """
        # Create subscription with past expiration date
        subscription_data = {
            'subscription_id': str(uuid4()),
            'user_id': sample_user_id,
            'plan_id': 'premium',
            'tier': 'premium',
            'status': 'active',
            'expires_at': datetime.now() - timedelta(days=1)  # Expired yesterday
        }
        
        # Directly insert expired subscription
        from app.services.payment_service import _subscriptions
        _subscriptions[sample_user_id] = subscription_data
        
        # Check status
        result = await payment_service.check_subscription_status(sample_user_id)
        
        # Assert
        assert result['active'] is False
        assert result['tier'] == 'free'  # Should default to free

    @pytest.mark.asyncio
    async def test_get_subscription_benefits(self, payment_service):
        """
        Test retrieving subscription benefits for different tiers.
        
        Should return correct features and limits for each tier.
        """
        # Test free tier
        free_benefits = payment_service.get_subscription_benefits("free")
        assert free_benefits['tier'] == "free"
        assert free_benefits['daily_credits'] == 0
        
        # Test premium tier
        premium_benefits = payment_service.get_subscription_benefits("premium")
        assert premium_benefits['tier'] == "premium"
        assert premium_benefits['daily_credits'] == 100
        assert "long-term memory" in [f.lower() for f in premium_benefits['features']]
        
        # Test VIP tier
        vip_benefits = payment_service.get_subscription_benefits("vip")
        assert vip_benefits['tier'] == "vip"
        assert vip_benefits['daily_credits'] == 300

    @pytest.mark.asyncio
    async def test_tier_comparison(self, payment_service):
        """
        Test tier hierarchy comparison functionality.
        
        Should correctly compare tier levels.
        """
        assert payment_service.is_tier_higher_or_equal("vip", "premium") is True
        assert payment_service.is_tier_higher_or_equal("premium", "free") is True
        assert payment_service.is_tier_higher_or_equal("free", "premium") is False
        assert payment_service.is_tier_higher_or_equal("premium", "premium") is True

    @pytest.mark.asyncio
    async def test_transaction_history(self, payment_service, sample_user_id):
        """
        Test retrieving transaction history.
        
        Should return list of user's payment transactions.
        """
        # Make some transactions
        await payment_service.purchase_credits(sample_user_id, "pack_60")
        await payment_service.purchase_credits(sample_user_id, "pack_300")
        
        # Get transaction history
        history = await payment_service.get_transaction_history(sample_user_id)
        
        # Assert
        assert len(history) == 2
        assert all('transaction_id' in tx for tx in history)
        assert all('amount' in tx for tx in history)
        assert all('credits_added' in tx for tx in history)

    @pytest.mark.asyncio
    async def test_daily_credit_refresh(self, payment_service, sample_user_id):
        """
        Test daily credit refresh for subscription users.
        
        Should add daily credits based on subscription tier.
        """
        # Create premium subscription (100 daily credits)
        await payment_service.create_subscription(
            sample_user_id, "premium", "monthly"
        )
        
        # Refresh daily credits
        result = await payment_service.refresh_daily_credits(sample_user_id)
        
        # Assert
        assert result['success'] is True
        assert result['credits_added'] == 100
        
        # Verify wallet balance
        wallet = await payment_service.get_wallet_balance(sample_user_id)
        assert wallet['credits'] >= 100

    @pytest.mark.asyncio
    async def test_subscription_renewal(self, payment_service, sample_user_id):
        """
        Test automatic subscription renewal.
        
        Should extend subscription period and maintain active status.
        """
        # Create subscription near expiration
        await payment_service.create_subscription(
            sample_user_id, "premium", "monthly"
        )
        
        # Simulate renewal
        result = await payment_service.renew_subscription(sample_user_id)
        
        # Assert
        assert result['success'] is True
        assert 'renewed' in result['message'].lower()
        
        # Verify subscription is still active with extended period
        subscription = await payment_service.get_subscription(sample_user_id)
        assert subscription['status'] == "active"
        assert subscription['expires_at'] > datetime.now()

    @pytest.mark.asyncio
    async def test_refund_processing(self, payment_service, sample_user_id):
        """
        Test processing refunds for credit purchases.
        
        Should deduct credits and record refund transaction.
        """
        # Purchase credits first
        await payment_service.purchase_credits(sample_user_id, "pack_300")
        
        # Process refund
        result = await payment_service.process_refund(
            sample_user_id, 
            credits_to_refund=330,
            reason="user_request"
        )
        
        # Assert
        assert result['success'] is True
        assert result['credits_refunded'] == 330
        
        # Verify credits were deducted
        wallet = await payment_service.get_wallet_balance(sample_user_id)
        assert wallet['credits'] == 0