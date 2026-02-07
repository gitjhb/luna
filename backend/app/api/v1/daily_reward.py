"""
Daily Login Reward API
每日登录奖励 - 订阅用户每天登录送月石
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-reward")

# 奖励配置
DAILY_REWARD_CREDITS = {
    "free": 0,       # 免费用户不送
    "premium": 10,   # Premium 送 10
    "vip": 20,       # VIP 送 20
}

# 内存记录（生产环境用数据库）
# {user_id: "2026-02-06"}
_claimed_dates: Dict[str, str] = {}


async def _get_last_claim_date(user_id: str) -> Optional[str]:
    """获取用户上次领取日期"""
    # 先检查内存
    if user_id in _claimed_dates:
        return _claimed_dates[user_id]
    
    # 检查数据库
    from app.core.database import get_db
    from sqlalchemy import text
    
    try:
        async with get_db() as db:
            result = await db.execute(
                text("SELECT last_daily_reward_date FROM user_subscriptions WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row and row[0]:
                return row[0]
    except Exception as e:
        logger.warning(f"Failed to get last claim date from DB: {e}")
    
    return None


async def _save_claim_date(user_id: str, claim_date: str):
    """保存领取日期"""
    _claimed_dates[user_id] = claim_date
    
    # 保存到数据库
    from app.core.database import get_db
    from sqlalchemy import text
    
    try:
        async with get_db() as db:
            await db.execute(
                text("""
                    UPDATE user_subscriptions 
                    SET last_daily_reward_date = :claim_date 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id, "claim_date": claim_date}
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to save claim date to DB: {e}")


@router.get("/status")
async def get_daily_reward_status(req: Request) -> Dict[str, Any]:
    """
    获取每日奖励状态
    返回今天是否可以领取、奖励数量等
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # 获取订阅状态
    from app.services.subscription_service import subscription_service
    tier = await subscription_service.get_effective_tier(user_id)
    
    # 计算奖励
    reward_amount = DAILY_REWARD_CREDITS.get(tier, 0)
    
    # 检查今天是否已领取
    today = date.today().isoformat()
    last_claim = await _get_last_claim_date(user_id)
    already_claimed = last_claim == today
    
    return {
        "success": True,
        "tier": tier,
        "reward_amount": reward_amount,
        "can_claim": reward_amount > 0 and not already_claimed,
        "already_claimed": already_claimed,
        "last_claim_date": last_claim,
    }


@router.post("/claim")
async def claim_daily_reward(req: Request) -> Dict[str, Any]:
    """
    领取每日奖励
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # 获取订阅状态
    from app.services.subscription_service import subscription_service
    tier = await subscription_service.get_effective_tier(user_id)
    
    # 计算奖励
    reward_amount = DAILY_REWARD_CREDITS.get(tier, 0)
    
    if reward_amount <= 0:
        return {
            "success": False,
            "message": "订阅用户才能领取每日奖励哦~",
            "reward_amount": 0,
        }
    
    # 检查今天是否已领取
    today = date.today().isoformat()
    last_claim = await _get_last_claim_date(user_id)
    
    if last_claim == today:
        return {
            "success": False,
            "message": "今天已经领取过了，明天再来吧~",
            "reward_amount": 0,
            "already_claimed": True,
        }
    
    # 发放奖励
    from app.services.payment_service import payment_service
    wallet = await payment_service.add_credits(
        user_id=user_id,
        amount=reward_amount,
        is_purchased=False,  # 是赠送的
        description=f"每日登录奖励 ({tier})"
    )
    
    # 记录领取日期
    await _save_claim_date(user_id, today)
    
    logger.info(f"User {user_id} claimed daily reward: {reward_amount} credits")
    
    return {
        "success": True,
        "message": f"恭喜获得 {reward_amount} 月石！",
        "reward_amount": reward_amount,
        "tier": tier,
        "new_balance": wallet.get("total_credits", 0),
    }
