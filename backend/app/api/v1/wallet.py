"""
Wallet / Billing API Routes
"""

from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from typing import List

from app.models.schemas import (
    WalletBalance, TransactionRecord,
    PurchaseRequest, PurchaseResponse,
    SubscriptionInfo
)

router = APIRouter(prefix="/wallet")

# Mock wallet data (per-user in production)
_mock_wallet = {
    "total_credits": 50.0,
    "daily_free_credits": 10.0,
    "purchased_credits": 40.0,
    "bonus_credits": 0.0,
    "subscription_tier": "free",
    "daily_limit": 10.0,
}

_mock_transactions: List[dict] = []


@router.get("/balance", response_model=WalletBalance)
async def get_balance():
    """Get current wallet balance"""
    return WalletBalance(**_mock_wallet)


@router.get("/transactions", response_model=List[TransactionRecord])
async def get_transactions(limit: int = 20, offset: int = 0):
    """Get transaction history"""
    return [
        TransactionRecord(**t)
        for t in _mock_transactions[offset : offset + limit]
    ]


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
