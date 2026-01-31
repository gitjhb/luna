"""
Payment API Routes - Subscriptions, Purchases, Gifts
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.services.payment_service import (
    payment_service,
    SUBSCRIPTION_PLANS,
    CREDIT_PACKAGES,
    MOCK_PAYMENT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment")


# ============================================================================
# Request/Response Models
# ============================================================================

class PurchaseRequest(BaseModel):
    package_id: str
    payment_provider: str = "mock"
    provider_transaction_id: Optional[str] = None


class SubscribeRequest(BaseModel):
    plan_id: str
    billing_period: str = "monthly"  # monthly or yearly
    payment_provider: str = "mock"
    provider_transaction_id: Optional[str] = None


class SendGiftRequest(BaseModel):
    character_id: str
    gift_type: str
    gift_price: int
    xp_reward: int


class WalletResponse(BaseModel):
    user_id: str
    total_credits: int
    purchased_credits: int
    bonus_credits: int
    daily_free_credits: int


class SubscriptionResponse(BaseModel):
    user_id: str
    tier: str
    started_at: Optional[str]
    expires_at: Optional[str]
    auto_renew: bool
    is_active: bool


# ============================================================================
# Info Endpoints
# ============================================================================

@router.get("/config")
async def get_payment_config():
    """Get payment configuration (mock mode status, available packages/plans)"""
    return {
        "mock_mode": MOCK_PAYMENT,
        "credit_packages": list(CREDIT_PACKAGES.values()),
        "subscription_plans": list(SUBSCRIPTION_PLANS.values()),
    }


@router.get("/plans")
async def get_available_plans(req: Request):
    """Get subscription plans available for the current user"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    plans = await payment_service.get_available_plans(user_id)
    return {"plans": plans}


# ============================================================================
# Wallet Endpoints
# ============================================================================

@router.get("/wallet")
async def get_wallet(req: Request):
    """Get current user's wallet"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    wallet = await payment_service.get_wallet(user_id)
    return wallet


@router.post("/wallet/add-credits")
async def add_credits(amount: int, req: Request):
    """Add credits to wallet (for testing/admin)"""
    if not MOCK_PAYMENT:
        raise HTTPException(status_code=403, detail="Only available in mock mode")
    
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    wallet = await payment_service.add_credits(user_id, amount, is_purchased=False)
    return {"success": True, "wallet": wallet}


# ============================================================================
# Purchase Endpoints
# ============================================================================

@router.post("/purchase")
async def purchase_credits(request: PurchaseRequest, req: Request):
    """Purchase a credit package"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        result = await payment_service.purchase_credits(
            user_id=user_id,
            package_id=request.package_id,
            payment_provider=request.payment_provider,
            provider_transaction_id=request.provider_transaction_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


# ============================================================================
# Subscription Endpoints
# ============================================================================

@router.get("/subscription")
async def get_subscription(req: Request):
    """Get current subscription status"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    subscription = await payment_service.get_subscription(user_id)
    return subscription


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, req: Request):
    """Subscribe to a plan"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        result = await payment_service.subscribe(
            user_id=user_id,
            plan_id=request.plan_id,
            billing_period=request.billing_period,
            payment_provider=request.payment_provider,
            provider_transaction_id=request.provider_transaction_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.post("/subscription/cancel")
async def cancel_subscription(req: Request):
    """Cancel subscription (will expire at end of billing period)"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    result = await payment_service.cancel_subscription(user_id)
    return result


# ============================================================================
# Transaction History
# ============================================================================

@router.get("/transactions")
async def get_transactions(limit: int = 20, offset: int = 0, req: Request = None):
    """Get transaction history"""
    user = getattr(req.state, "user", None) if req else None
    user_id = str(user.user_id) if user else "demo-user-123"
    
    transactions = await payment_service.get_transactions(user_id, limit, offset)
    return {"transactions": transactions, "total": len(transactions)}
