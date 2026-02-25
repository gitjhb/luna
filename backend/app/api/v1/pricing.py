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

@router.get("/config", response_model=PricingConfig,
           summary="Get complete pricing and subscription options",
           description="""
           Retrieve all available pricing options including credit packages and subscription plans.
           
           **Credit Packages (One-time Purchase):**
           - Credits never expire once purchased
           - Bonus credits included with larger packages
           - Popular packages highlighted for better conversion
           - Prices in USD, processed via Stripe
           
           **Package Tiers:**
           - **Starter** (60 credits): $0.99 - Perfect for trying premium features
           - **Value** (300 credits): $4.99 - Most popular for casual users  
           - **Premium** (980 credits): $14.99 - Best value with bonus credits
           - **Power User** (1980 credits): $29.99 - For heavy users
           - **Ultimate** (3280 credits): $49.99 - Maximum single purchase
           - **Whale** (6480 credits): $99.99 - VIP tier with 20% bonus
           
           **Subscription Plans (Recurring):**
           
           **Free Tier:**
           - 10 daily credits (resets every 24h)
           - Basic characters and safe content only
           - Standard support
           
           **Premium ($4.99/month):**
           - 50 daily credits + keep unused credits
           - Access to spicy content (18+)
           - All characters including premium exclusives
           - Priority chat responses
           - Voice message support
           - Email support
           
           **VIP ($9.99/month):**  
           - 100 daily credits + unlimited carryover
           - Early access to new features
           - Exclusive VIP-only characters
           - Custom avatar generation
           - Direct developer feedback channel
           - 50% discount on credit packages
           
           **Regional Pricing:** Prices may vary by region/currency
           **Payment Methods:** Credit cards, Apple Pay, Google Pay via Stripe
           """,
           responses={
               200: {"description": "Complete pricing configuration with all packages and plans"}
           })
async def get_pricing_config():
    """Get all available pricing options and subscription plans."""
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
