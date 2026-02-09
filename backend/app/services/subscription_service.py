"""
Subscription Service - Single Source of Truth for Subscription Status
=====================================================================

统一的订阅状态查询服务，解决订阅状态不一致的问题。

核心原则：
1. 订阅等级严格按照 UserSubscription 表的 tier + expires_at 来判断
2. 所有订阅状态变更都要记录到账单 (TransactionHistory)
3. 提供统一的 get_effective_tier() 方法，供各处调用

Author: Claude
Date: 2025
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)

# Mock mode for testing - default to FALSE to use database
MOCK_MODE = os.getenv("MOCK_PAYMENT", "false").lower() == "true"
logger.info(f"SubscriptionService MOCK_MODE: {MOCK_MODE}")


class SubscriptionTier(str, Enum):
    """订阅等级枚举"""
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"


# Tier hierarchy for comparison
TIER_HIERARCHY = {
    SubscriptionTier.FREE: 0,
    "free": 0,
    SubscriptionTier.PREMIUM: 1,
    "premium": 1,
    SubscriptionTier.VIP: 2,
    "vip": 2,
}

# Tier benefits
TIER_BENEFITS = {
    "free": {
        "daily_credits": 0,
        "nsfw_enabled": False,
        "premium_characters": False,
        "priority_response": False,
        "extended_memory": False,
    },
    "premium": {
        "daily_credits": 100,
        "nsfw_enabled": True,
        "premium_characters": True,
        "priority_response": True,
        "extended_memory": True,
    },
    "vip": {
        "daily_credits": 300,
        "nsfw_enabled": True,
        "premium_characters": True,
        "priority_response": True,
        "extended_memory": True,
        "early_access": True,
    },
}

# In-memory storage for mock mode
_mock_subscriptions: Dict[str, dict] = {}


class SubscriptionService:
    """
    统一的订阅状态服务 - Single Source of Truth
    
    所有需要判断用户订阅等级的地方，都应该调用这个服务。
    
    Usage:
        from app.services.subscription_service import subscription_service
        
        # 获取有效的订阅等级
        tier = await subscription_service.get_effective_tier(user_id)
        
        # 检查是否有权限
        has_access = await subscription_service.has_feature(user_id, "nsfw_enabled")
        
        # 检查是否是付费用户
        is_premium = await subscription_service.is_subscribed(user_id)
    """
    
    # ========================================================================
    # Core Query Methods
    # ========================================================================
    
    async def get_effective_tier(self, user_id: str) -> str:
        """
        获取用户的有效订阅等级
        
        这是判断订阅等级的唯一入口！
        
        逻辑：
        1. 查询 UserSubscription 表
        2. 检查是否过期
        3. 如果过期，自动降级为 free 并记录账单
        4. 返回有效的 tier
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: "free", "premium", or "vip"
        """
        subscription = await self._get_subscription_record(user_id)
        
        if not subscription:
            return SubscriptionTier.FREE.value
        
        tier = subscription.get("tier", "free")
        expires_at = subscription.get("expires_at")
        
        # Free tier is always valid
        if tier == "free":
            return SubscriptionTier.FREE.value
        
        # Check expiration
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            
            if datetime.utcnow() > expires_at:
                # Subscription expired - downgrade to free
                logger.info(f"Subscription expired for user {user_id}, downgrading to free")
                await self._handle_subscription_expiry(user_id, tier)
                return SubscriptionTier.FREE.value
        
        return tier
    
    async def get_subscription_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取完整的订阅信息
        
        Returns:
            {
                "user_id": str,
                "tier": str,
                "effective_tier": str,  # 考虑过期后的实际等级
                "is_subscribed": bool,
                "is_active": bool,
                "started_at": datetime,
                "expires_at": datetime,
                "auto_renew": bool,
                "benefits": dict,
            }
        """
        subscription = await self._get_subscription_record(user_id)
        effective_tier = await self.get_effective_tier(user_id)
        
        if not subscription:
            return {
                "user_id": user_id,
                "tier": "free",
                "effective_tier": "free",
                "is_subscribed": False,
                "is_active": True,  # Free is always active
                "started_at": None,
                "expires_at": None,
                "auto_renew": False,
                "benefits": TIER_BENEFITS["free"],
            }
        
        stored_tier = subscription.get("tier", "free")
        is_subscribed = effective_tier != "free"
        is_active = effective_tier == stored_tier  # True if not expired
        
        return {
            "user_id": user_id,
            "tier": stored_tier,
            "effective_tier": effective_tier,
            "is_subscribed": is_subscribed,
            "is_active": is_active,
            "started_at": subscription.get("started_at"),
            "expires_at": subscription.get("expires_at"),
            "auto_renew": subscription.get("auto_renew", False),
            "benefits": TIER_BENEFITS.get(effective_tier, TIER_BENEFITS["free"]),
        }
    
    async def is_subscribed(self, user_id: str) -> bool:
        """
        检查用户是否有付费订阅
        
        Returns:
            bool: True if user has premium or vip subscription
        """
        tier = await self.get_effective_tier(user_id)
        return tier in ["premium", "vip"]
    
    async def has_feature(self, user_id: str, feature: str) -> bool:
        """
        检查用户是否有某个功能的权限
        
        Args:
            user_id: 用户ID
            feature: 功能名称 (nsfw_enabled, premium_characters, etc.)
            
        Returns:
            bool: 是否有权限
        """
        tier = await self.get_effective_tier(user_id)
        benefits = TIER_BENEFITS.get(tier, TIER_BENEFITS["free"])
        return benefits.get(feature, False)
    
    async def get_tier_level(self, user_id: str) -> int:
        """
        获取订阅等级的数值（用于比较）
        
        Returns:
            int: 0=free, 1=premium, 2=vip
        """
        tier = await self.get_effective_tier(user_id)
        return TIER_HIERARCHY.get(tier, 0)
    
    async def compare_tier(self, user_id: str, required_tier: str) -> bool:
        """
        检查用户等级是否满足要求
        
        Args:
            user_id: 用户ID
            required_tier: 要求的最低等级
            
        Returns:
            bool: 用户等级 >= 要求等级
        """
        user_level = await self.get_tier_level(user_id)
        required_level = TIER_HIERARCHY.get(required_tier, 0)
        return user_level >= required_level
    
    # ========================================================================
    # Subscription Mutation Methods
    # ========================================================================
    
    async def activate_subscription(
        self,
        user_id: str,
        tier: str,
        duration_days: int,
        payment_provider: str = "mock",
        provider_transaction_id: str = None,
        price: float = 0.0,
    ) -> Dict[str, Any]:
        """
        激活订阅
        
        会记录账单到 TransactionHistory
        
        Args:
            user_id: 用户ID
            tier: 订阅等级
            duration_days: 持续天数
            payment_provider: 支付提供商
            provider_transaction_id: 支付流水号
            price: 价格
            
        Returns:
            订阅信息
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=duration_days)
        
        # Get current subscription to check for upgrade
        old_sub = await self._get_subscription_record(user_id)
        old_tier = old_sub.get("tier", "free") if old_sub else "free"
        
        # Create or update subscription
        subscription_data = {
            "user_id": user_id,
            "tier": tier,
            "started_at": now,
            "expires_at": expires_at,
            "auto_renew": True,
            "payment_provider": payment_provider,
            "provider_subscription_id": provider_transaction_id,
            "is_active": True,
            "updated_at": now,
        }
        
        await self._save_subscription_record(user_id, subscription_data)
        
        # Record transaction
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="subscription",
            description=f"订阅激活: {tier} ({duration_days}天)",
            extra_data={
                "old_tier": old_tier,
                "new_tier": tier,
                "duration_days": duration_days,
                "payment_provider": payment_provider,
                "provider_transaction_id": provider_transaction_id,
                "price": price,
            }
        )
        
        logger.info(f"Subscription activated: user={user_id}, tier={tier}, expires={expires_at}")
        
        return await self.get_subscription_info(user_id)
    
    async def cancel_subscription(
        self,
        user_id: str,
        immediate: bool = True,
        reason: str = None,
    ) -> Dict[str, Any]:
        """
        取消订阅
        
        Args:
            user_id: 用户ID
            immediate: 是否立即取消（否则等到期后自动取消）
            reason: 取消原因
            
        Returns:
            订阅信息
        """
        subscription = await self._get_subscription_record(user_id)
        if not subscription or subscription.get("tier") == "free":
            return {
                "success": False,
                "message": "No active subscription to cancel",
            }
        
        old_tier = subscription.get("tier")
        now = datetime.utcnow()
        
        if immediate:
            # Immediately downgrade to free
            subscription["tier"] = "free"
            subscription["is_active"] = False
            subscription["auto_renew"] = False
            subscription["updated_at"] = now
        else:
            # Just stop auto-renew
            subscription["auto_renew"] = False
            subscription["updated_at"] = now
        
        await self._save_subscription_record(user_id, subscription)
        
        # Record transaction
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="subscription_cancel",
            description=f"订阅取消: {old_tier} -> free" if immediate else f"订阅自动续费关闭",
            extra_data={
                "old_tier": old_tier,
                "new_tier": "free" if immediate else old_tier,
                "immediate": immediate,
                "reason": reason,
            }
        )
        
        logger.info(f"Subscription cancelled: user={user_id}, immediate={immediate}")
        
        return {
            "success": True,
            "subscription": await self.get_subscription_info(user_id),
        }
    
    async def update_auto_renew(self, user_id: str, auto_renew: bool) -> Dict[str, Any]:
        """
        更新自动续费状态（从 App Store/Play Store 通知调用）
        
        Args:
            user_id: 用户ID
            auto_renew: 是否自动续费
            
        Returns:
            更新后的订阅信息
        """
        subscription = await self._get_subscription_record(user_id)
        if not subscription:
            return {"success": False, "message": "No subscription found"}
        
        subscription["auto_renew"] = auto_renew
        subscription["updated_at"] = datetime.utcnow()
        
        await self._save_subscription_record(user_id, subscription)
        
        # Record transaction
        action = "enabled" if auto_renew else "disabled"
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="auto_renew_change",
            description=f"自动续费{action}",
            extra_data={"auto_renew": auto_renew}
        )
        
        logger.info(f"Auto-renew updated: user={user_id}, auto_renew={auto_renew}")
        
        return {
            "success": True,
            "auto_renew": auto_renew,
            "subscription": await self.get_subscription_info(user_id),
        }
    
    async def expire_subscription(self, user_id: str, reason: str = None) -> Dict[str, Any]:
        """
        让订阅过期（从 App Store/Play Store 通知调用）
        
        用于：
        - 订阅自然过期
        - 用户退款
        - 家庭共享权限被移除
        
        Args:
            user_id: 用户ID
            reason: 过期原因 (expired, refund, revoked)
            
        Returns:
            操作结果
        """
        subscription = await self._get_subscription_record(user_id)
        if not subscription:
            return {"success": True, "message": "No subscription to expire"}
        
        old_tier = subscription.get("tier", "free")
        if old_tier == "free":
            return {"success": True, "message": "Already free tier"}
        
        now = datetime.utcnow()
        
        # Downgrade to free
        subscription["tier"] = "free"
        subscription["is_active"] = False
        subscription["auto_renew"] = False
        subscription["updated_at"] = now
        
        await self._save_subscription_record(user_id, subscription)
        
        # Record transaction
        reason_text = {
            "expired": "订阅到期",
            "refund": "用户退款",
            "revoked": "权限撤销",
        }.get(reason, "订阅终止")
        
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="subscription_expired",
            description=f"{reason_text}: {old_tier} -> free",
            extra_data={
                "old_tier": old_tier,
                "new_tier": "free",
                "reason": reason,
            }
        )
        
        logger.info(f"Subscription expired: user={user_id}, reason={reason}")
        
        return {
            "success": True,
            "old_tier": old_tier,
            "new_tier": "free",
            "reason": reason,
        }
    
    async def mark_billing_issue(self, user_id: str) -> Dict[str, Any]:
        """
        标记订阅有账单问题（续费失败，在 grace period）
        
        不会立即取消订阅，但会记录状态。
        可以用来触发用户通知。
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        subscription = await self._get_subscription_record(user_id)
        if not subscription:
            return {"success": False, "message": "No subscription found"}
        
        subscription["billing_issue"] = True
        subscription["billing_issue_at"] = datetime.utcnow()
        subscription["updated_at"] = datetime.utcnow()
        
        await self._save_subscription_record(user_id, subscription)
        
        # Record transaction
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="billing_issue",
            description="续费失败，请更新支付方式",
            extra_data={"tier": subscription.get("tier")}
        )
        
        logger.warning(f"Billing issue marked: user={user_id}")
        
        # TODO: 可以在这里触发推送通知提醒用户更新支付方式
        
        return {
            "success": True,
            "message": "Billing issue marked",
            "tier": subscription.get("tier"),
        }
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    async def _get_subscription_record(self, user_id: str) -> Optional[dict]:
        """从数据库或 mock 存储获取订阅记录"""
        if MOCK_MODE:
            return _mock_subscriptions.get(user_id)
        
        # Use database
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.payment_models import UserSubscription
        
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserSubscription).where(UserSubscription.user_id == user_id)
                )
                sub = result.scalar_one_or_none()
                
                if sub:
                    return sub.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get subscription record: {e}")
            return None
    
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Handle ISO format strings
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    async def _save_subscription_record(self, user_id: str, data: dict):
        """保存订阅记录到数据库或 mock 存储"""
        if MOCK_MODE:
            _mock_subscriptions[user_id] = data
            return
        
        # Use database
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.payment_models import UserSubscription
        
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserSubscription).where(UserSubscription.user_id == user_id)
                )
                sub = result.scalar_one_or_none()
                
                if not sub:
                    sub = UserSubscription(user_id=user_id)
                    db.add(sub)
                
                sub.tier = data.get("tier", "free")
                # Convert datetime strings back to datetime objects for SQLite
                sub.started_at = self._parse_datetime(data.get("started_at"))
                sub.expires_at = self._parse_datetime(data.get("expires_at"))
                sub.auto_renew = data.get("auto_renew", False)
                sub.payment_provider = data.get("payment_provider")
                sub.provider_subscription_id = data.get("provider_subscription_id")
                
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save subscription record: {e}")
    
    async def _handle_subscription_expiry(self, user_id: str, old_tier: str):
        """处理订阅过期 - 降级并记录账单"""
        now = datetime.utcnow()
        
        # Update subscription to free
        subscription = await self._get_subscription_record(user_id) or {}
        subscription["tier"] = "free"
        subscription["is_active"] = False
        subscription["updated_at"] = now
        
        await self._save_subscription_record(user_id, subscription)
        
        # Record transaction
        await self._record_subscription_transaction(
            user_id=user_id,
            transaction_type="subscription_expired",
            description=f"订阅过期: {old_tier} -> free",
            extra_data={
                "old_tier": old_tier,
                "new_tier": "free",
                "expired_at": now.isoformat(),
            }
        )
    
    async def _record_subscription_transaction(
        self,
        user_id: str,
        transaction_type: str,
        description: str,
        extra_data: dict = None,
    ):
        """记录订阅相关的账单"""
        if MOCK_MODE:
            # In mock mode, just log
            logger.info(f"[MOCK] Transaction: user={user_id}, type={transaction_type}, desc={description}")
            return
        
        # Use database
        from app.core.database import get_db
        from app.models.database.billing_models import TransactionHistory, TransactionType
        
        try:
            async with get_db() as db:
                # Map our transaction types to existing enum
                type_mapping = {
                    "subscription": TransactionType.PURCHASE,
                    "subscription_cancel": TransactionType.REFUND,
                    "subscription_expired": TransactionType.DEDUCTION,  # 权益到期/失去
                }
                tx_type = type_mapping.get(transaction_type, TransactionType.PURCHASE)
                
                transaction = TransactionHistory(
                    user_id=user_id,
                    transaction_type=tx_type,
                    amount=0.0,  # Subscription changes don't affect credit balance
                    balance_after=0.0,  # Will be updated if needed
                    description=description,
                    extra_data=extra_data or {},
                )
                db.add(transaction)
                await db.commit()
                
                logger.info(f"Recorded subscription transaction: user={user_id}, type={transaction_type}")
        except Exception as e:
            logger.error(f"Failed to record transaction: {e}")


# Singleton instance - use this everywhere!
subscription_service = SubscriptionService()


# ============================================================================
# Testing/Debug Methods
# ============================================================================

async def set_mock_subscription(user_id: str, tier: str, expires_in_days: int = 30):
    """
    设置 mock 订阅状态（仅用于测试）
    
    Args:
        user_id: 用户ID
        tier: 订阅等级 (free, premium, vip)
        expires_in_days: 过期天数
    """
    if not MOCK_MODE:
        logger.warning("set_mock_subscription called in non-mock mode, ignoring")
        return
    
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    _mock_subscriptions[user_id] = {
        "user_id": user_id,
        "tier": tier,
        "started_at": now,
        "expires_at": now + timedelta(days=expires_in_days) if tier != "free" else None,
        "auto_renew": tier != "free",
        "is_active": True,
        "updated_at": now,
    }
    logger.info(f"[MOCK] Set subscription: user={user_id}, tier={tier}")


# ============================================================================
# Helper Functions for Quick Access
# ============================================================================

async def get_user_tier(user_id: str) -> str:
    """快捷方法：获取用户订阅等级"""
    return await subscription_service.get_effective_tier(user_id)


async def is_premium_user(user_id: str) -> bool:
    """快捷方法：检查是否是付费用户"""
    return await subscription_service.is_subscribed(user_id)


async def can_access_nsfw(user_id: str) -> bool:
    """快捷方法：检查是否可以访问 NSFW 内容"""
    return await subscription_service.has_feature(user_id, "nsfw_enabled")
