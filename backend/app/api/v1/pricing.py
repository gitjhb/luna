"""
Pricing API Routes - Credit packages and subscription plans
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/pricing")


class CoinPack(BaseModel):
    """Coin pack for purchase - matches frontend interface"""
    id: str
    coins: int
    price: float  # USD
    bonusCoins: Optional[int] = None
    discount: Optional[int] = None
    popular: bool = False


class MembershipPlan(BaseModel):
    """Membership plan - matches frontend interface"""
    id: str
    tier: str  # free, premium, vip
    name: str
    price: float  # USD per month
    dailyCredits: int
    features: List[str]
    highlighted: bool = False


class PricingConfig(BaseModel):
    """Full pricing configuration - matches frontend PricingConfig"""
    coinPacks: List[CoinPack]
    membershipPlans: List[MembershipPlan]


# ============================================================================
# Pricing Data
# ============================================================================

COIN_PACKS = [
    CoinPack(id="pack_60", coins=60, price=0.99),
    CoinPack(id="pack_300", coins=300, price=4.99, bonusCoins=30),
    CoinPack(id="pack_980", coins=980, price=14.99, bonusCoins=110, popular=True),
    CoinPack(id="pack_1980", coins=1980, price=29.99, bonusCoins=260),
    CoinPack(id="pack_3280", coins=3280, price=49.99, bonusCoins=600),
    CoinPack(id="pack_6480", coins=6480, price=99.99, bonusCoins=1600, discount=20),
]

MEMBERSHIP_PLANS = [
    MembershipPlan(
        id="free",
        tier="free",
        name="Free",
        price=0,
        dailyCredits=10,
        features=[
            "10 daily credits",
            "Basic characters",
            "Standard response speed",
        ],
    ),
    MembershipPlan(
        id="premium",
        tier="premium",
        name="Premium",
        price=9.99,
        dailyCredits=100,
        highlighted=True,
        features=[
            "100 daily credits",
            "All characters unlocked",
            "Fast response speed",
            "Long-term memory",
            "Spicy mode",
        ],
    ),
    MembershipPlan(
        id="vip",
        tier="vip",
        name="VIP",
        price=19.99,
        dailyCredits=300,
        features=[
            "300 daily credits",
            "All characters unlocked",
            "Priority response speed",
            "Extended memory (10x)",
            "Spicy mode",
            "Early access to new features",
        ],
    ),
]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/config", response_model=PricingConfig)
async def get_pricing_config():
    """Get full pricing configuration for the app"""
    return PricingConfig(
        coinPacks=COIN_PACKS,
        membershipPlans=MEMBERSHIP_PLANS,
    )


@router.get("/packages", response_model=List[CoinPack])
async def get_coin_packs():
    """Get available coin packages"""
    return COIN_PACKS


@router.get("/plans", response_model=List[MembershipPlan])
async def get_membership_plans():
    """Get available membership plans"""
    return MEMBERSHIP_PLANS
