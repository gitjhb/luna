"""
Wallet / Billing API Routes
"""

from fastapi import APIRouter, HTTPException, Request
from uuid import uuid4
from datetime import datetime
from typing import List

from app.models.schemas import (
    WalletBalance, TransactionRecord,
    PurchaseRequest, PurchaseResponse,
    SubscriptionInfo
)
from app.services.payment_service import payment_service

router = APIRouter(prefix="/wallet")


@router.get("/balance", response_model=WalletBalance,
           summary="Get user's wallet balance and credits",
           description="""
           Retrieve the current wallet balance including all credit types and subscription info.
           
           **Credit Types:**
           - **Daily Free Credits**: Refreshed every 24 hours, tier-dependent amount
           - **Purchased Credits**: Bought through in-app purchases, never expire  
           - **Bonus Credits**: Promotional or referral rewards
           - **Total Credits**: Sum of all available credits for spending
           
           **Subscription Tiers:**
           - **Free**: 10 daily credits, basic features
           - **Premium**: 50 daily credits, spicy content, priority support
           - **VIP**: 100 daily credits, exclusive characters, early features
           
           **Usage:**
           - Each chat message typically costs 1-3 credits
           - Image generation costs 5-10 credits  
           - Voice messages cost 2-5 credits
           - Spicy content requires Premium+ subscription
           
           **Credit Refresh:**
           Daily credits reset at midnight user's timezone.
           """,
           responses={
               200: {"description": "Current wallet balance and credit breakdown"},
               401: {"description": "Authentication required"}
           })
async def get_balance(req: Request):
    """Get current wallet balance, credits, and subscription info."""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    wallet = await payment_service.get_wallet(user_id)
    subscription = await payment_service.get_subscription(user_id)
    
    return WalletBalance(
        total_credits=wallet.get("total_credits", 0),
        daily_free_credits=wallet.get("daily_free_credits", 10),
        purchased_credits=wallet.get("purchased_credits", 0),
        bonus_credits=wallet.get("bonus_credits", 0),
        subscription_tier=subscription.get("tier", "free"),
        daily_limit=wallet.get("daily_free_credits", 10),
    )


@router.get("/transactions", response_model=List[TransactionRecord])
async def get_transactions(limit: int = 20, offset: int = 0, req: Request = None):
    """Get transaction history"""
    user = getattr(req.state, "user", None) if req else None
    user_id = str(user.user_id) if user else "demo-user-123"
    
    transactions = await payment_service.get_transactions(user_id, limit, offset)
    result = []
    for t in transactions:
        # Handle created_at - could be datetime, string, or None
        created_at = t.get("created_at")
        if created_at is None:
            created_at = datetime.utcnow()
        elif isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.utcnow()
        
        result.append(TransactionRecord(
            transaction_id=t.get("transaction_id") or t.get("id") or str(uuid4()),
            transaction_type=t.get("type") or t.get("transaction_type") or "unknown",
            amount=t.get("amount", 0),
            balance_after=t.get("balance_after", 0),
            description=t.get("description", ""),
            created_at=created_at,
        ))
    return result


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_credits(request: PurchaseRequest):
    """Purchase credit package"""
    packages = {
        "pack_100": {"credits": 100, "price": 1.99},
        "pack_500": {"credits": 500, "price": 7.99},
        "pack_1500": {"credits": 1500, "price": 19.99},
    }

    pkg = packages.get(request.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    # Mock purchase (in production: integrate Stripe/IAP)
    old_balance = _mock_wallet["total_credits"]
    _mock_wallet["purchased_credits"] += pkg["credits"]
    _mock_wallet["total_credits"] += pkg["credits"]

    tx_id = uuid4()
    _mock_transactions.insert(0, {
        "transaction_id": tx_id,
        "transaction_type": "purchase",
        "amount": pkg["credits"],
        "balance_after": _mock_wallet["total_credits"],
        "description": f"购买 {pkg['credits']} 积分 (${pkg['price']})",
        "created_at": datetime.utcnow(),
    })

    return PurchaseResponse(
        success=True,
        new_balance=_mock_wallet["total_credits"],
        transaction_id=tx_id,
    )


@router.get("/subscription", response_model=SubscriptionInfo)
async def get_subscription(req: Request):
    """
    Get current subscription info
    
    Uses unified subscription service for accurate tier info.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    from app.services.subscription_service import subscription_service
    info = await subscription_service.get_subscription_info(user_id)
    
    return SubscriptionInfo(
        tier=info.get("effective_tier", "free"),
        expires_at=info.get("expires_at"),
        auto_renew=info.get("auto_renew", False),
    )


@router.post("/subscribe/{plan_id}")
async def subscribe(plan_id: str, req: Request):
    """
    Subscribe to a plan
    
    Uses unified subscription service.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    plans = {
        "basic": {"tier": "premium", "duration_days": 30},
        "pro": {"tier": "premium", "duration_days": 30},
        "vip": {"tier": "vip", "duration_days": 30},
    }

    plan = plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    from app.services.subscription_service import subscription_service
    info = await subscription_service.activate_subscription(
        user_id=user_id,
        tier=plan["tier"],
        duration_days=plan["duration_days"],
        payment_provider="mock",
    )

    return {
        "status": "subscribed",
        "tier": info.get("effective_tier"),
        "expires_at": info.get("expires_at"),
    }


@router.get("/subscription/debug")
async def debug_subscription(req: Request):
    """
    Debug endpoint: Get detailed subscription info
    
    Returns all subscription-related info for debugging.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    from app.services.subscription_service import subscription_service
    info = await subscription_service.get_subscription_info(user_id)
    
    return {
        "user_id": user_id,
        "subscription": info,
        "debug": {
            "tier_from_request_state": getattr(user, "subscription_tier", "N/A") if user else "N/A",
            "is_subscribed_from_request_state": getattr(user, "is_subscribed", "N/A") if user else "N/A",
        }
    }
