"""
Referral Service
================

Handles referral code generation, validation, and reward distribution.

⚠️ IMPORTANT: All coin rewards MUST go through payment_service and create TransactionHistory records.
金币 = 钱，必须落账单！

Author: Clawdbot
Date: January 31, 2025
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
from uuid import uuid4

from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)

# Referral reward configuration
REFERRAL_REWARD_AMOUNT = 50  # Coins given to referrer when someone signs up with their code
REFERRAL_NEW_USER_BONUS = 20  # Extra coins given to the new user who uses a referral code

# Mock mode for development
MOCK_REFERRAL = os.getenv("MOCK_REFERRAL", "false").lower() == "true"

# In-memory storage for mock mode
_mock_referrals: Dict[str, dict] = {}  # user_id -> referral info
_mock_code_to_user: Dict[str, str] = {}  # referral_code -> user_id
_mock_rewards: List[dict] = []


class ReferralService:
    """Service for managing user referrals"""
    
    async def get_or_create_referral_code(self, user_id: str) -> dict:
        """
        Get user's referral code, creating one if it doesn't exist.
        
        Returns:
            {
                "referral_code": str,
                "total_referrals": int,
                "total_rewards_earned": float
            }
        """
        if MOCK_REFERRAL:
            return await self._mock_get_or_create_code(user_id)
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.referral_models import UserReferral, generate_referral_code
        
        async with get_db() as db:
            # Try to find existing referral record
            result = await db.execute(
                select(UserReferral).where(UserReferral.user_id == user_id)
            )
            referral = result.scalar_one_or_none()
            
            if not referral:
                # Create new referral record with unique code
                referral = UserReferral(
                    user_id=user_id,
                    referral_code=generate_referral_code(),
                )
                db.add(referral)
                await db.commit()
                await db.refresh(referral)
                logger.info(f"Created referral code {referral.referral_code} for user {user_id}")
            
            return {
                "referral_code": referral.referral_code,
                "total_referrals": referral.total_referrals,
                "total_rewards_earned": referral.total_rewards_earned,
            }
    
    async def apply_referral_code(self, new_user_id: str, referral_code: str) -> dict:
        """
        Apply a referral code for a new user.
        
        This will:
        1. Validate the code exists and is not the user's own code
        2. Check if user hasn't already used a referral code
        3. Award coins to the referrer (via payment_service)
        4. Award bonus coins to the new user (via payment_service)
        5. Record the referral relationship
        
        Args:
            new_user_id: The new user who is using the code
            referral_code: The referral code to apply
            
        Returns:
            {"success": bool, "message": str, "reward_amount": int, ...}
        """
        referral_code = referral_code.upper().strip()
        
        if MOCK_REFERRAL:
            return await self._mock_apply_code(new_user_id, referral_code)
        
        from app.core.database import get_db
        from sqlalchemy import select, update
        from app.models.database.referral_models import UserReferral, ReferralReward
        from app.models.database.billing_models import TransactionHistory, TransactionType
        
        async with get_db() as db:
            # Find the referrer by code
            result = await db.execute(
                select(UserReferral).where(UserReferral.referral_code == referral_code)
            )
            referrer_record = result.scalar_one_or_none()
            
            if not referrer_record:
                return {"success": False, "message": "无效的邀请码", "error": "invalid_code"}
            
            referrer_user_id = referrer_record.user_id
            
            # Check: can't use your own code
            if referrer_user_id == new_user_id:
                return {"success": False, "message": "不能使用自己的邀请码", "error": "self_referral"}
            
            # Check: new user hasn't already been referred
            result = await db.execute(
                select(UserReferral).where(UserReferral.user_id == new_user_id)
            )
            new_user_referral = result.scalar_one_or_none()
            
            if new_user_referral and new_user_referral.referred_by_user_id:
                return {"success": False, "message": "您已经使用过邀请码了", "error": "already_referred"}
            
            # Create referral record for new user if doesn't exist
            if not new_user_referral:
                new_user_referral = UserReferral(
                    user_id=new_user_id,
                    referred_by_user_id=referrer_user_id,
                    referred_at=datetime.utcnow(),
                )
                db.add(new_user_referral)
            else:
                new_user_referral.referred_by_user_id = referrer_user_id
                new_user_referral.referred_at = datetime.utcnow()
            
            # ========================================
            # 💰 CRITICAL: Award coins via wallet service
            # ========================================
            
            # 1. Award referrer
            try:
                referrer_wallet = await payment_service.add_credits(
                    user_id=referrer_user_id,
                    amount=REFERRAL_REWARD_AMOUNT,
                    is_purchased=False,  # This is bonus credits
                    description=f"邀请好友奖励 (+{REFERRAL_REWARD_AMOUNT}金币)"
                )
                logger.info(f"Awarded {REFERRAL_REWARD_AMOUNT} coins to referrer {referrer_user_id}")
            except Exception as e:
                logger.error(f"Failed to award referrer: {e}")
                await db.rollback()
                return {"success": False, "message": "奖励发放失败，请稍后重试", "error": "reward_failed"}
            
            # 2. Award new user bonus
            try:
                new_user_wallet = await payment_service.add_credits(
                    user_id=new_user_id,
                    amount=REFERRAL_NEW_USER_BONUS,
                    is_purchased=False,
                    description=f"使用邀请码奖励 (+{REFERRAL_NEW_USER_BONUS}金币)"
                )
                logger.info(f"Awarded {REFERRAL_NEW_USER_BONUS} coins to new user {new_user_id}")
            except Exception as e:
                logger.error(f"Failed to award new user: {e}")
                # Don't rollback here - referrer already got their reward
            
            # Update referrer's stats
            referrer_record.total_referrals += 1
            referrer_record.total_rewards_earned += REFERRAL_REWARD_AMOUNT
            
            # Record the reward event
            reward_record = ReferralReward(
                referrer_user_id=referrer_user_id,
                referred_user_id=new_user_id,
                reward_amount=REFERRAL_REWARD_AMOUNT,
                reward_type="signup",
                is_paid=True,
            )
            db.add(reward_record)
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"邀请码使用成功！获得{REFERRAL_NEW_USER_BONUS}金币奖励",
                "referrer_reward": REFERRAL_REWARD_AMOUNT,
                "new_user_bonus": REFERRAL_NEW_USER_BONUS,
                "new_balance": new_user_wallet.get("total_credits", 0),
            }
    
    async def get_referred_friends(self, user_id: str, limit: int = 50, offset: int = 0) -> dict:
        """
        Get list of friends referred by this user.
        
        Returns:
            {
                "friends": [...],
                "total_count": int,
                "total_rewards": float
            }
        """
        if MOCK_REFERRAL:
            return await self._mock_get_friends(user_id, limit, offset)
        
        from app.core.database import get_db
        from sqlalchemy import select, func
        from app.models.database.referral_models import UserReferral, ReferralReward
        from app.models.database.billing_models import User
        
        async with get_db() as db:
            # Get referral record for stats
            result = await db.execute(
                select(UserReferral).where(UserReferral.user_id == user_id)
            )
            my_referral = result.scalar_one_or_none()
            
            if not my_referral:
                return {
                    "friends": [],
                    "total_count": 0,
                    "total_rewards": 0.0,
                }
            
            # Get all users referred by this user
            result = await db.execute(
                select(UserReferral, User)
                .join(User, UserReferral.user_id == User.user_id)
                .where(UserReferral.referred_by_user_id == user_id)
                .order_by(UserReferral.referred_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = result.all()
            
            friends = []
            for referral, user in rows:
                # Get reward info for this referral
                reward_result = await db.execute(
                    select(ReferralReward)
                    .where(ReferralReward.referrer_user_id == user_id)
                    .where(ReferralReward.referred_user_id == referral.user_id)
                )
                reward = reward_result.scalar_one_or_none()
                
                friends.append({
                    "user_id": user.user_id,
                    "display_name": user.display_name or "用户",
                    "avatar_url": user.avatar_url,
                    "referred_at": referral.referred_at.isoformat() if referral.referred_at else None,
                    "reward_earned": reward.reward_amount if reward else REFERRAL_REWARD_AMOUNT,
                })
            
            return {
                "friends": friends,
                "total_count": my_referral.total_referrals,
                "total_rewards": my_referral.total_rewards_earned,
            }
    
    async def get_referral_stats(self, user_id: str) -> dict:
        """Get referral statistics for a user"""
        referral_info = await self.get_or_create_referral_code(user_id)
        friends_info = await self.get_referred_friends(user_id, limit=0)
        
        return {
            "referral_code": referral_info["referral_code"],
            "total_referrals": referral_info["total_referrals"],
            "total_rewards_earned": referral_info["total_rewards_earned"],
            "reward_per_referral": REFERRAL_REWARD_AMOUNT,
            "new_user_bonus": REFERRAL_NEW_USER_BONUS,
        }
    
    # ========================================
    # Mock implementations for development
    # ========================================
    
    async def _mock_get_or_create_code(self, user_id: str) -> dict:
        """Mock implementation"""
        if user_id not in _mock_referrals:
            from app.models.database.referral_models import generate_referral_code
            code = generate_referral_code()
            _mock_referrals[user_id] = {
                "user_id": user_id,
                "referral_code": code,
                "total_referrals": 0,
                "total_rewards_earned": 0.0,
                "referred_by_user_id": None,
            }
            _mock_code_to_user[code] = user_id
            logger.info(f"[MOCK] Created referral code {code} for user {user_id}")
        
        info = _mock_referrals[user_id]
        return {
            "referral_code": info["referral_code"],
            "total_referrals": info["total_referrals"],
            "total_rewards_earned": info["total_rewards_earned"],
        }
    
    async def _mock_apply_code(self, new_user_id: str, referral_code: str) -> dict:
        """Mock implementation"""
        referral_code = referral_code.upper().strip()
        
        if referral_code not in _mock_code_to_user:
            return {"success": False, "message": "无效的邀请码", "error": "invalid_code"}
        
        referrer_user_id = _mock_code_to_user[referral_code]
        
        if referrer_user_id == new_user_id:
            return {"success": False, "message": "不能使用自己的邀请码", "error": "self_referral"}
        
        # Create record for new user
        await self._mock_get_or_create_code(new_user_id)
        
        if _mock_referrals[new_user_id].get("referred_by_user_id"):
            return {"success": False, "message": "您已经使用过邀请码了", "error": "already_referred"}
        
        _mock_referrals[new_user_id]["referred_by_user_id"] = referrer_user_id
        
        # Award coins (via payment_service which handles mock mode)
        await payment_service.add_credits(
            user_id=referrer_user_id,
            amount=REFERRAL_REWARD_AMOUNT,
            is_purchased=False,
            description=f"邀请好友奖励 (+{REFERRAL_REWARD_AMOUNT}金币)"
        )
        
        new_user_wallet = await payment_service.add_credits(
            user_id=new_user_id,
            amount=REFERRAL_NEW_USER_BONUS,
            is_purchased=False,
            description=f"使用邀请码奖励 (+{REFERRAL_NEW_USER_BONUS}金币)"
        )
        
        # Update referrer stats
        _mock_referrals[referrer_user_id]["total_referrals"] += 1
        _mock_referrals[referrer_user_id]["total_rewards_earned"] += REFERRAL_REWARD_AMOUNT
        
        # Record reward
        _mock_rewards.append({
            "referrer_user_id": referrer_user_id,
            "referred_user_id": new_user_id,
            "reward_amount": REFERRAL_REWARD_AMOUNT,
            "created_at": datetime.utcnow(),
        })
        
        logger.info(f"[MOCK] Referral applied: {referrer_user_id} referred {new_user_id}")
        
        return {
            "success": True,
            "message": f"邀请码使用成功！获得{REFERRAL_NEW_USER_BONUS}金币奖励",
            "referrer_reward": REFERRAL_REWARD_AMOUNT,
            "new_user_bonus": REFERRAL_NEW_USER_BONUS,
            "new_balance": new_user_wallet.get("total_credits", 0),
        }
    
    async def _mock_get_friends(self, user_id: str, limit: int, offset: int) -> dict:
        """Mock implementation"""
        if user_id not in _mock_referrals:
            return {"friends": [], "total_count": 0, "total_rewards": 0.0}
        
        friends = []
        for uid, info in _mock_referrals.items():
            if info.get("referred_by_user_id") == user_id:
                # Find reward
                reward = next(
                    (r for r in _mock_rewards 
                     if r["referrer_user_id"] == user_id and r["referred_user_id"] == uid),
                    None
                )
                friends.append({
                    "user_id": uid,
                    "display_name": f"用户{uid[:8]}",
                    "avatar_url": None,
                    "referred_at": reward["created_at"].isoformat() if reward else None,
                    "reward_earned": REFERRAL_REWARD_AMOUNT,
                })
        
        my_info = _mock_referrals[user_id]
        return {
            "friends": friends[offset:offset + limit] if limit > 0 else [],
            "total_count": my_info["total_referrals"],
            "total_rewards": my_info["total_rewards_earned"],
        }


# Singleton instance
referral_service = ReferralService()
