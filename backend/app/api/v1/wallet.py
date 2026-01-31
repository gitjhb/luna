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


@router.get("/balance", response_model=WalletBalance)
async def get_balance(req: Request):
    """Get current wallet balance"""
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
async def get_subscription():
    """Get current subscription info"""
    return SubscriptionInfo(
        tier=_mock_wallet["subscription_tier"],
        expires_at=None,
        auto_renew=False,
    )


@router.post("/subscribe/{plan_id}")
async def subscribe(plan_id: str):
    """Subscribe to a plan (mock)"""
    plans = {
        "basic": {"tier": "premium", "daily": 100},
        "pro": {"tier": "premium", "daily": 300},
        "vip": {"tier": "vip", "daily": 1000},
    }

    plan = plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    _mock_wallet["subscription_tier"] = plan["tier"]
    _mock_wallet["daily_limit"] = plan["daily"]

    return {"status": "subscribed", "tier": plan["tier"]}
