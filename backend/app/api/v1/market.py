"""
Market API Routes - Credit packages and subscription plans
"""

from fastapi import APIRouter
from typing import List

from app.models.schemas import CreditPackage, SubscriptionPlan

router = APIRouter(prefix="/market")


CREDIT_PACKAGES = [
    CreditPackage(
        package_id="pack_100",
        credits=100,
        price_usd=1.99,
        label="100 积分",
        discount_percent=0,
    ),
    CreditPackage(
        package_id="pack_500",
        credits=500,
        price_usd=7.99,
        label="500 积分",
        discount_percent=20,
    ),
    CreditPackage(
        package_id="pack_1500",
        credits=1500,
        price_usd=19.99,
        label="1500 积分",
        discount_percent=33,
    ),
]

SUBSCRIPTION_PLANS = [
    SubscriptionPlan(
        plan_id="free",
        name="免费版",
        tier="free",
        price_monthly_usd=0,
        daily_credits=10,
        features=["基础对话", "标准角色"],
    ),
    SubscriptionPlan(
        plan_id="basic",
        name="基础版",
        tier="premium",
        price_monthly_usd=9.99,
        daily_credits=100,
        features=["基础对话", "语音消息", "记忆功能", "全部角色"],
    ),
    SubscriptionPlan(
        plan_id="pro",
        name="专业版",
        tier="premium",
        price_monthly_usd=19.99,
        daily_credits=300,
        features=["全部功能", "图片生成", "优先响应", "无广告"],
    ),
    SubscriptionPlan(
        plan_id="vip",
        name="VIP",
        tier="vip",
        price_monthly_usd=49.99,
        daily_credits=1000,
        features=["全部功能", "专属角色", "API 访问", "1对1支持"],
    ),
]


@router.get("/packages", response_model=List[CreditPackage])
async def list_credit_packages():
    """List available credit packages"""
    return CREDIT_PACKAGES


@router.get("/plans", response_model=List[SubscriptionPlan])
async def list_subscription_plans():
    """List available subscription plans"""
    return SUBSCRIPTION_PLANS


@router.get("/costs")
async def get_feature_costs():
    """Get credit costs for each feature"""
    return {
        "chat": 2,
        "chat_long": 4,
        "voice_tts": 5,
        "voice_stt": 3,
        "image_gen": 10,
        "memory_recall": 0,
    }
