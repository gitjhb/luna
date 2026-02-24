"""
Daily Login Reward API - 限时签到活动
活动期间每天签到送50月石，简单直接
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily")

# ==================== 活动配置 ====================
# 修改这里来更换活动
EVENT_CONFIG = {
    "name": "🎊 新春签到活动",
    "reward": 50,                    # 每天奖励月石数
    "start_date": "2026-02-23",      # 活动开始日期
    "end_date": "2026-03-01",        # 活动结束日期（共7天）
    "max_days": 7,                   # 最多签到天数
}
# ================================================

# 内存缓存（生产环境用数据库）
_user_checkin_data: Dict[str, Dict[str, Any]] = {}


def is_event_active() -> bool:
    """检查活动是否进行中"""
    today = date.today().isoformat()
    return EVENT_CONFIG["start_date"] <= today <= EVENT_CONFIG["end_date"]


def get_event_days_left() -> int:
    """获取活动剩余天数"""
    today = date.today()
    end_date = date.fromisoformat(EVENT_CONFIG["end_date"])
    diff = (end_date - today).days + 1  # 包含今天
    return max(0, diff)


async def _get_checkin_data(user_id: str) -> Dict[str, Any]:
    """获取用户签到数据"""
    # 先检查内存缓存
    if user_id in _user_checkin_data:
        return _user_checkin_data[user_id]
    
    default_data = {"last_claim": None, "event_checkins": 0, "total_rewards": 0}
    
    # 检查数据库
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        
        async with get_db() as db:
            result = await db.execute(
                text("""
                    SELECT last_daily_reward_date, consecutive_checkin_days 
                    FROM user_subscriptions 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row:
                data = {
                    "last_claim": row[0],
                    "event_checkins": row[1] or 0,
                    "total_rewards": (row[1] or 0) * EVENT_CONFIG["reward"],
                }
                _user_checkin_data[user_id] = data
                return data
    except Exception as e:
        logger.warning(f"Failed to get checkin data from DB: {e}")
    
    _user_checkin_data[user_id] = default_data
    return default_data


async def _save_checkin_data(user_id: str, last_claim: str, event_checkins: int):
    """保存签到数据"""
    data = {
        "last_claim": last_claim, 
        "event_checkins": event_checkins,
        "total_rewards": event_checkins * EVENT_CONFIG["reward"]
    }
    _user_checkin_data[user_id] = data
    
    # 保存到数据库
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        
        async with get_db() as db:
            await db.execute(
                text("""
                    INSERT INTO user_subscriptions (user_id, last_daily_reward_date, consecutive_checkin_days) 
                    VALUES (:user_id, :last_claim, :event_checkins)
                    ON DUPLICATE KEY UPDATE 
                        last_daily_reward_date = :last_claim,
                        consecutive_checkin_days = :event_checkins
                """),
                {
                    "user_id": user_id, 
                    "last_claim": last_claim, 
                    "event_checkins": event_checkins
                }
            )
            await db.commit()
            logger.info(f"📅 Saved checkin: user {user_id}, day {event_checkins}")
    except Exception as e:
        logger.warning(f"Failed to save checkin data to DB: {e}")


@router.get("/status")
async def get_daily_reward_status(req: Request) -> Dict[str, Any]:
    """
    获取签到状态
    返回活动信息、今天是否可签到、已签到天数等
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # 检查活动是否进行中
    if not is_event_active():
        return {
            "success": True,
            "event_active": False,
            "event_name": EVENT_CONFIG["name"],
            "message": "活动已结束，敬请期待下次活动~",
            "can_claim": False,
        }
    
    # 获取签到数据
    checkin_data = await _get_checkin_data(user_id)
    last_claim = checkin_data["last_claim"]
    event_checkins = checkin_data["event_checkins"]
    
    # 检查今天是否已签到
    today = date.today().isoformat()
    already_claimed = last_claim == today
    
    # 是否还能签到（未签满且今天没签）
    can_claim = not already_claimed and event_checkins < EVENT_CONFIG["max_days"]
    
    return {
        "success": True,
        "event_active": True,
        "event_name": EVENT_CONFIG["name"],
        "reward_amount": EVENT_CONFIG["reward"],
        "can_claim": can_claim,
        "already_claimed": already_claimed,
        "last_claim_date": last_claim,
        "event_checkins": event_checkins,
        "max_days": EVENT_CONFIG["max_days"],
        "days_left": get_event_days_left(),
        "total_rewards": checkin_data["total_rewards"],
    }


@router.post("/checkin")
async def claim_daily_reward(req: Request) -> Dict[str, Any]:
    """
    每日签到领取奖励
    活动期间每天50月石，最多签到7天
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # 检查活动是否进行中
    if not is_event_active():
        return {
            "success": False,
            "message": "活动已结束，敬请期待下次活动~",
            "reward_amount": 0,
        }
    
    # 获取签到数据
    checkin_data = await _get_checkin_data(user_id)
    last_claim = checkin_data["last_claim"]
    event_checkins = checkin_data["event_checkins"]
    
    # 检查今天是否已签到
    today = date.today().isoformat()
    if last_claim == today:
        return {
            "success": False,
            "message": "今天已经签到过啦～明天再来哦 💕",
            "reward_amount": 0,
            "already_claimed": True,
            "event_checkins": event_checkins,
        }
    
    # 检查是否签满
    if event_checkins >= EVENT_CONFIG["max_days"]:
        return {
            "success": False,
            "message": f"本次活动你已签满 {EVENT_CONFIG['max_days']} 天啦～感谢参与！🎉",
            "reward_amount": 0,
            "event_checkins": event_checkins,
        }
    
    # 计算奖励
    reward_amount = EVENT_CONFIG["reward"]
    new_checkins = event_checkins + 1
    
    # 发放奖励
    try:
        from app.services.payment_service import payment_service
        wallet = await payment_service.add_credits(
            user_id=user_id,
            amount=reward_amount,
            is_purchased=False,
            description=f"签到活动第{new_checkins}天"
        )
        new_balance = wallet.get("total_credits", 0)
    except Exception as e:
        logger.error(f"Failed to add credits: {e}")
        return {
            "success": False,
            "message": "签到失败，请稍后再试~",
            "reward_amount": 0,
        }
    
    # 保存签到数据
    await _save_checkin_data(user_id, today, new_checkins)
    
    # 计算剩余
    remaining = EVENT_CONFIG["max_days"] - new_checkins
    days_left = get_event_days_left()
    
    # 生成消息
    if remaining == 0:
        message = f"🎊 恭喜集齐全部 {EVENT_CONFIG['max_days']} 天奖励！\n💎 +{reward_amount} 月石"
    else:
        message = f"🎉 签到成功！\n💎 +{reward_amount} 月石\n📅 已签 {new_checkins}/{EVENT_CONFIG['max_days']} 天"
    
    logger.info(f"User {user_id} checkin day {new_checkins}: +{reward_amount} credits")
    
    return {
        "success": True,
        "message": message,
        "reward_amount": reward_amount,
        "new_balance": new_balance,
        "event_checkins": new_checkins,
        "max_days": EVENT_CONFIG["max_days"],
        "remaining": remaining,
        "days_left": days_left,
        "is_complete": remaining == 0,
    }
