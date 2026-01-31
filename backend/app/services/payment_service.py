"""
Payment Service - Handles subscriptions and purchases
Mock mode for testing, ready for real payment integration
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from uuid import uuid4

logger = logging.getLogger(__name__)

# Mock mode - skip real payment processing  
# Default to FALSE so it uses real database
MOCK_PAYMENT = os.getenv("MOCK_PAYMENT", "false").lower() == "true"
logger.info(f"Payment service MOCK_PAYMENT: {MOCK_PAYMENT}")

# In-memory storage (replace with DB in production)
_subscriptions: Dict[str, dict] = {}
_wallets: Dict[str, dict] = {}
_transactions: List[dict] = []


# ============================================================================
# Subscription Plans
# ============================================================================

SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "tier": "free",
        "price_monthly": 0,
        "price_yearly": 0,
        "daily_credits": 10,
        "features": [
            "10 daily credits",
            "Basic characters",
            "Standard response speed",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "tier": "premium",
        "price_monthly": 9.99,
        "price_yearly": 79.99,
        "daily_credits": 100,
        "features": [
            "100 daily credits",
            "All characters unlocked",
            "Fast response speed",
            "Long-term memory",
            "Spicy mode",
        ],
    },
    "vip": {
        "id": "vip",
        "name": "VIP",
        "tier": "vip",
        "price_monthly": 19.99,
        "price_yearly": 149.99,
        "daily_credits": 300,
        "features": [
            "300 daily credits",
            "All characters unlocked",
            "Priority response speed",
            "Extended memory (10x)",
            "Spicy mode",
            "Early access to new features",
        ],
    },
}

# Tier hierarchy for comparison
TIER_HIERARCHY = {"free": 0, "premium": 1, "vip": 2}


# ============================================================================
# Credit Packages
# ============================================================================

CREDIT_PACKAGES = {
    "pack_60": {"id": "pack_60", "coins": 60, "price": 0.99, "bonus": 0},
    "pack_300": {"id": "pack_300", "coins": 300, "price": 4.99, "bonus": 30},
    "pack_980": {"id": "pack_980", "coins": 980, "price": 14.99, "bonus": 110},
    "pack_1980": {"id": "pack_1980", "coins": 1980, "price": 29.99, "bonus": 260},
    "pack_3280": {"id": "pack_3280", "coins": 3280, "price": 49.99, "bonus": 600},
    "pack_6480": {"id": "pack_6480", "coins": 6480, "price": 99.99, "bonus": 1600},
}


class PaymentService:
    """Payment and subscription management service"""
    
    # ========================================================================
    # Wallet Operations
    # ========================================================================
    
    async def get_or_create_wallet(self, user_id: str) -> dict:
        """Get or create user wallet"""
        if MOCK_PAYMENT:
            # Use in-memory storage for mock mode
            if user_id not in _wallets:
                _wallets[user_id] = {
                    "user_id": user_id,
                    "total_credits": 50,  # Initial free credits (新用户奖励)
                    "purchased_credits": 0,
                    "bonus_credits": 0,
                    "daily_free_credits": 10,
                    "daily_credits_used": 0,
                    "daily_reset_at": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            return _wallets[user_id]
        
        # Use database for real mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.billing_models import UserWallet
        
        async with get_db() as db:
            result = await db.execute(
                select(UserWallet).where(UserWallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            
            if not wallet:
                # Create new wallet with initial credits (新用户奖励50金币)
                wallet = UserWallet(
                    user_id=user_id,
                    total_credits=50.0,  # Initial free credits (新用户奖励)
                    purchased_credits=0.0,
                    free_credits=10.0,
                    daily_refresh_amount=10.0,
                )
                db.add(wallet)
                await db.commit()
                await db.refresh(wallet)
                logger.info(f"Created new wallet for user {user_id} with 50 credits (新用户奖励)")
            
            return {
                "user_id": wallet.user_id,
                "total_credits": wallet.total_credits,
                "purchased_credits": wallet.purchased_credits,
                "bonus_credits": wallet.free_credits,  # Map free_credits to bonus_credits for API compat
                "daily_free_credits": wallet.daily_refresh_amount,
                "daily_credits_used": 0,
                "daily_reset_at": datetime.utcnow(),
                "created_at": wallet.created_at,
                "updated_at": wallet.updated_at,
            }
    
    async def get_wallet(self, user_id: str) -> Optional[dict]:
        """Get user wallet"""
        return await self.get_or_create_wallet(user_id)
    
    async def add_credits(self, user_id: str, amount: int, is_purchased: bool = True, description: str = None) -> dict:
        """Add credits to user wallet"""
        if MOCK_PAYMENT:
            wallet = await self.get_or_create_wallet(user_id)
            wallet["total_credits"] += amount
            if is_purchased:
                wallet["purchased_credits"] += amount
            else:
                wallet["bonus_credits"] += amount
            wallet["updated_at"] = datetime.utcnow()
            return wallet
        
        # Use database for real mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
        
        async with get_db() as db:
            result = await db.execute(
                select(UserWallet).where(UserWallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            
            if not wallet:
                wallet = UserWallet(
                    user_id=user_id,
                    total_credits=0.0,
                    purchased_credits=0.0,
                    free_credits=10.0,
                    daily_refresh_amount=10.0,
                )
                db.add(wallet)
            
            wallet.total_credits += amount
            if is_purchased:
                wallet.purchased_credits += amount
            else:
                wallet.free_credits += amount
            wallet.updated_at = datetime.utcnow()
            
            # Record transaction
            transaction = TransactionHistory(
                user_id=user_id,
                transaction_type=TransactionType.PURCHASE if is_purchased else TransactionType.BONUS,
                amount=amount,
                balance_after=wallet.total_credits,
                description=description or ("Purchase credits" if is_purchased else "Bonus credits"),
            )
            db.add(transaction)
            await db.commit()
            
            return {
                "user_id": wallet.user_id,
                "total_credits": wallet.total_credits,
                "purchased_credits": wallet.purchased_credits,
                "bonus_credits": wallet.free_credits,
                "daily_free_credits": wallet.daily_refresh_amount,
            }
    
    async def deduct_credits(self, user_id: str, amount: int, description: str = None) -> dict:
        """Deduct credits from user wallet"""
        if MOCK_PAYMENT:
            wallet = await self.get_or_create_wallet(user_id)
            if wallet["total_credits"] < amount:
                raise ValueError(f"Insufficient credits: {wallet['total_credits']} < {amount}")
            wallet["total_credits"] -= amount
            wallet["updated_at"] = datetime.utcnow()
            return wallet
        
        # Use database for real mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
        
        async with get_db() as db:
            result = await db.execute(
                select(UserWallet).where(UserWallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            
            if not wallet or wallet.total_credits < amount:
                current = wallet.total_credits if wallet else 0
                raise ValueError(f"Insufficient credits: {current} < {amount}")
            
            wallet.total_credits -= amount
            wallet.updated_at = datetime.utcnow()
            
            # Record transaction
            transaction = TransactionHistory(
                user_id=user_id,
                transaction_type=TransactionType.DEDUCTION,
                amount=-amount,
                balance_after=wallet.total_credits,
                description=description or "Credit deduction",
            )
            db.add(transaction)
            await db.commit()
            
            return {
                "user_id": wallet.user_id,
                "total_credits": wallet.total_credits,
                "purchased_credits": wallet.purchased_credits,
                "bonus_credits": wallet.free_credits,
                "daily_free_credits": wallet.daily_refresh_amount,
            }
    
    # ========================================================================
    # Subscription Operations
    # ========================================================================
    
    async def get_subscription(self, user_id: str) -> dict:
        """Get user subscription status"""
        if user_id not in _subscriptions:
            _subscriptions[user_id] = {
                "user_id": user_id,
                "tier": "free",
                "started_at": None,
                "expires_at": None,
                "auto_renew": False,
                "payment_provider": None,
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
        
        sub = _subscriptions[user_id]
        
        # Check if subscription expired
        if sub["tier"] != "free" and sub["expires_at"]:
            if datetime.utcnow() > sub["expires_at"]:
                sub["tier"] = "free"
                sub["is_active"] = True  # Free is always active
                logger.info(f"Subscription expired for user {user_id}")
        
        sub["is_active"] = sub["tier"] == "free" or (
            sub["expires_at"] and datetime.utcnow() < sub["expires_at"]
        )
        
        return sub
    
    async def subscribe(
        self,
        user_id: str,
        plan_id: str,
        billing_period: str = "monthly",  # monthly or yearly
        payment_provider: str = "mock",
        provider_transaction_id: str = None,
    ) -> dict:
        """Subscribe user to a plan"""
        
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")
        
        plan = SUBSCRIPTION_PLANS[plan_id]
        current_sub = await self.get_subscription(user_id)
        
        # Check tier hierarchy - can't downgrade to lower tier
        current_tier_level = TIER_HIERARCHY.get(current_sub["tier"], 0)
        new_tier_level = TIER_HIERARCHY.get(plan["tier"], 0)
        
        if new_tier_level < current_tier_level and current_sub["is_active"]:
            raise ValueError(f"Cannot downgrade from {current_sub['tier']} to {plan['tier']} while subscription is active")
        
        # Calculate price and duration
        if billing_period == "yearly":
            price = plan["price_yearly"]
            duration = timedelta(days=365)
        else:
            price = plan["price_monthly"]
            duration = timedelta(days=30)
        
        # In mock mode, skip actual payment
        if MOCK_PAYMENT:
            logger.info(f"[MOCK] Processing subscription: {plan_id} for user {user_id}")
            provider_transaction_id = f"mock_sub_{uuid4().hex[:8]}"
        else:
            # TODO: Call real payment provider (Apple/Google/Stripe)
            # This is where you'd integrate with:
            # - Apple StoreKit for iOS
            # - Google Play Billing for Android
            # - Stripe for web
            raise NotImplementedError("Real payment not implemented yet")
        
        # Update subscription
        now = datetime.utcnow()
        _subscriptions[user_id] = {
            "user_id": user_id,
            "tier": plan["tier"],
            "started_at": now,
            "expires_at": now + duration,
            "auto_renew": True,
            "payment_provider": payment_provider,
            "provider_subscription_id": provider_transaction_id,
            "is_active": True,
            "created_at": current_sub.get("created_at", now),
            "updated_at": now,
        }
        
        # Record transaction
        transaction = {
            "id": str(uuid4()),
            "user_id": user_id,
            "transaction_type": "subscription",
            "amount": price,
            "credits": 0,
            "description": f"Subscribe to {plan['name']} ({billing_period})",
            "payment_provider": payment_provider,
            "provider_transaction_id": provider_transaction_id,
            "status": "completed",
            "created_at": now,
        }
        _transactions.append(transaction)
        
        # Update wallet daily credits based on new tier
        wallet = await self.get_or_create_wallet(user_id)
        wallet["daily_free_credits"] = plan["daily_credits"]
        
        logger.info(f"User {user_id} subscribed to {plan_id}")
        
        return {
            "success": True,
            "subscription": _subscriptions[user_id],
            "transaction": transaction,
        }
    
    async def cancel_subscription(self, user_id: str) -> dict:
        """Cancel subscription (will expire at end of period)"""
        sub = await self.get_subscription(user_id)
        
        if sub["tier"] == "free":
            return {"success": False, "message": "No active subscription to cancel"}
        
        sub["auto_renew"] = False
        sub["updated_at"] = datetime.utcnow()
        
        return {
            "success": True,
            "message": f"Subscription will expire on {sub['expires_at']}",
            "subscription": sub,
        }
    
    # ========================================================================
    # Purchase Operations
    # ========================================================================
    
    async def purchase_credits(
        self,
        user_id: str,
        package_id: str,
        payment_provider: str = "mock",
        provider_transaction_id: str = None,
    ) -> dict:
        """Purchase credit package"""
        
        if package_id not in CREDIT_PACKAGES:
            raise ValueError(f"Invalid package: {package_id}")
        
        package = CREDIT_PACKAGES[package_id]
        
        # In mock mode or dev mode, skip actual payment verification
        # TODO: In production, integrate with Apple/Google/Stripe for receipt validation
        if MOCK_PAYMENT:
            logger.info(f"[MOCK] Processing purchase: {package_id} for user {user_id}")
        else:
            logger.info(f"[DEV] Processing purchase without payment verification: {package_id} for user {user_id}")
        provider_transaction_id = provider_transaction_id or f"dev_purchase_{uuid4().hex[:8]}"
        
        # Add credits to wallet
        total_coins = package["coins"] + package["bonus"]
        description = f"购买 {package['coins']} 金币 (+{package['bonus']} 赠送)"
        wallet = await self.add_credits(user_id, total_coins, is_purchased=True, description=description)
        
        # Record transaction
        now = datetime.utcnow()
        transaction = {
            "id": str(uuid4()),
            "user_id": user_id,
            "transaction_type": "purchase",
            "amount": package["price"],
            "credits": total_coins,
            "description": description,
            "payment_provider": payment_provider,
            "provider_transaction_id": provider_transaction_id,
            "status": "completed",
            "created_at": now,
        }
        
        if MOCK_PAYMENT:
            _transactions.append(transaction)
        # Note: In non-mock mode, transaction is already recorded in add_credits()
        
        logger.info(f"User {user_id} purchased {package_id}: +{total_coins} credits")
        
        return {
            "success": True,
            "credits_added": total_coins,
            "wallet": wallet,
            "transaction": transaction,
        }
    
    # ========================================================================
    # Gift Operations
    # ========================================================================
    
    async def send_gift(
        self,
        user_id: str,
        character_id: str,
        gift_type: str,
        gift_price: int,
        xp_reward: int,
    ) -> dict:
        """Send a gift (deduct credits, award XP)"""
        
        wallet = await self.get_wallet(user_id)
        if wallet["total_credits"] < gift_price:
            return {
                "success": False,
                "message": f"Insufficient credits: {wallet['total_credits']} < {gift_price}",
            }
        
        # Deduct credits
        wallet = await self.deduct_credits(user_id, gift_price)
        
        # Record transaction
        now = datetime.utcnow()
        transaction = {
            "id": str(uuid4()),
            "user_id": user_id,
            "transaction_type": "gift",
            "amount": 0,  # Internal transaction, no real money
            "credits": -gift_price,
            "description": f"Sent {gift_type} to character {character_id}",
            "payment_provider": None,
            "status": "completed",
            "created_at": now,
        }
        _transactions.append(transaction)
        
        # TODO: Award XP via intimacy service
        # await intimacy_service.award_xp(user_id, character_id, "gift", xp_reward)
        
        return {
            "success": True,
            "credits_deducted": gift_price,
            "xp_awarded": xp_reward,
            "wallet": wallet,
            "transaction": transaction,
        }
    
    # ========================================================================
    # Transaction History
    # ========================================================================
    
    async def get_transactions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        """Get user transaction history"""
        if MOCK_PAYMENT:
            # Use in-memory storage for mock mode
            user_transactions = [t for t in _transactions if t["user_id"] == user_id]
            user_transactions.sort(key=lambda x: x["created_at"], reverse=True)
            return user_transactions[offset:offset + limit]
        
        # Use database for real mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.billing_models import TransactionHistory
        
        async with get_db() as db:
            result = await db.execute(
                select(TransactionHistory)
                .where(TransactionHistory.user_id == user_id)
                .order_by(TransactionHistory.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            transactions = result.scalars().all()
            return [
                {
                    "transaction_id": t.transaction_id,
                    "user_id": t.user_id,
                    "type": t.transaction_type.value if t.transaction_type else None,
                    "amount": t.amount,
                    "balance_after": t.balance_after,
                    "description": t.description,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in transactions
            ]
    
    # ========================================================================
    # Available Plans (for upgrade)
    # ========================================================================
    
    async def get_available_plans(self, user_id: str) -> List[dict]:
        """Get plans available for upgrade (excludes lower tiers)"""
        current_sub = await self.get_subscription(user_id)
        current_tier_level = TIER_HIERARCHY.get(current_sub["tier"], 0)
        
        available = []
        for plan_id, plan in SUBSCRIPTION_PLANS.items():
            tier_level = TIER_HIERARCHY.get(plan["tier"], 0)
            # Only show same or higher tiers
            if tier_level >= current_tier_level:
                plan_copy = plan.copy()
                plan_copy["is_current"] = plan["tier"] == current_sub["tier"]
                available.append(plan_copy)
        
        return available


# Singleton instance
payment_service = PaymentService()
