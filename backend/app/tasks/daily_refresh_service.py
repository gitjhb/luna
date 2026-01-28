"""
Daily Credit Refresh Service
============================

This service handles the daily refresh of free credits for users.
Can be implemented using:
1. Celery Beat (recommended for production)
2. Redis TTL (lightweight alternative)
3. Cron job (simple alternative)

Author: Manus AI
Date: January 28, 2026
"""

import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.database import User, UserWallet, TransactionHistory
from app.core.database import get_db_session

logger = logging.getLogger(__name__)


class DailyRefreshService:
    """Service to handle daily credit refresh for users"""
    
    def __init__(self, db_session_factory):
        """
        Initialize the daily refresh service.
        
        Args:
            db_session_factory: Factory function to create database sessions
        """
        self.db_session_factory = db_session_factory
    
    async def refresh_all_users(self) -> dict:
        """
        Refresh credits for all eligible users.
        
        Returns:
            Dictionary with refresh statistics
        """
        logger.info("Starting daily credit refresh for all users")
        
        stats = {
            "total_processed": 0,
            "total_refreshed": 0,
            "total_credits_added": 0.0,
            "errors": 0,
        }
        
        async with self.db_session_factory() as db:
            try:
                # Get all users with wallets that need refresh
                result = await db.execute(
                    select(UserWallet)
                    .options(selectinload(UserWallet.user))
                )
                wallets = result.scalars().all()
                
                for wallet in wallets:
                    stats["total_processed"] += 1
                    
                    try:
                        if wallet.needs_daily_refresh():
                            amount_added = await self._refresh_wallet(wallet, db)
                            
                            if amount_added > 0:
                                stats["total_refreshed"] += 1
                                stats["total_credits_added"] += amount_added
                                
                                logger.info(
                                    f"Refreshed {amount_added} credits for user {wallet.user_id} "
                                    f"(new balance: {wallet.total_credits})"
                                )
                    
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(
                            f"Error refreshing credits for user {wallet.user_id}: {str(e)}",
                            exc_info=True
                        )
                
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error in daily refresh: {str(e)}", exc_info=True)
                stats["errors"] += 1
        
        logger.info(
            f"Daily credit refresh completed: "
            f"{stats['total_refreshed']}/{stats['total_processed']} users refreshed, "
            f"{stats['total_credits_added']:.2f} total credits added, "
            f"{stats['errors']} errors"
        )
        
        return stats
    
    async def _refresh_wallet(self, wallet: UserWallet, db: AsyncSession) -> float:
        """
        Refresh a single wallet.
        
        Args:
            wallet: UserWallet instance
            db: Database session
            
        Returns:
            Amount of credits added
        """
        amount_added = wallet.apply_daily_refresh()
        
        if amount_added > 0:
            # Create transaction record
            transaction = TransactionHistory(
                user_id=wallet.user_id,
                transaction_type="daily_refresh",
                amount=amount_added,
                balance_after=wallet.total_credits,
                description="Daily free credits refresh",
                metadata={
                    "refresh_date": datetime.utcnow().isoformat(),
                }
            )
            db.add(transaction)
        
        return amount_added
    
    async def refresh_user(self, user_id: str) -> dict:
        """
        Refresh credits for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with refresh result
        """
        async with self.db_session_factory() as db:
            try:
                result = await db.execute(
                    select(UserWallet)
                    .where(UserWallet.user_id == user_id)
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    return {
                        "success": False,
                        "error": "Wallet not found",
                    }
                
                if not wallet.needs_daily_refresh():
                    return {
                        "success": True,
                        "refreshed": False,
                        "message": "Daily refresh not needed yet",
                        "next_refresh_in_hours": self._hours_until_refresh(wallet),
                    }
                
                amount_added = await self._refresh_wallet(wallet, db)
                await db.commit()
                
                return {
                    "success": True,
                    "refreshed": True,
                    "amount_added": amount_added,
                    "new_balance": wallet.total_credits,
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error refreshing user {user_id}: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }
    
    def _hours_until_refresh(self, wallet: UserWallet) -> float:
        """Calculate hours until next refresh"""
        if not wallet.last_daily_refresh:
            return 0.0
        
        now = datetime.utcnow()
        time_since_refresh = now - wallet.last_daily_refresh
        seconds_remaining = 86400 - time_since_refresh.total_seconds()
        return max(0.0, seconds_remaining / 3600)


# ==========================================
# Implementation Option 1: Celery Beat
# ==========================================

"""
# In celery_app.py

from celery import Celery
from celery.schedules import crontab
from app.services.daily_refresh_service import DailyRefreshService
from app.core.database import get_db_session

celery_app = Celery('ai_companion', broker='redis://localhost:6379/0')

celery_app.conf.beat_schedule = {
    'daily-credit-refresh': {
        'task': 'app.tasks.refresh_credits',
        'schedule': crontab(hour=0, minute=0),  # Run at midnight UTC
    },
}

@celery_app.task
def refresh_credits():
    service = DailyRefreshService(get_db_session)
    asyncio.run(service.refresh_all_users())
"""


# ==========================================
# Implementation Option 2: Redis TTL
# ==========================================

class RedisTTLRefreshService:
    """
    Alternative implementation using Redis TTL.
    
    This approach sets a TTL key for each user. When the key expires,
    the next request triggers a refresh.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_and_refresh(self, user_id: str, wallet: UserWallet, db: AsyncSession) -> float:
        """
        Check if user needs refresh and apply it.
        
        Args:
            user_id: User ID
            wallet: UserWallet instance
            db: Database session
            
        Returns:
            Amount of credits added (0 if no refresh needed)
        """
        refresh_key = f"daily_refresh:{user_id}"
        
        # Check if refresh key exists
        exists = await self.redis.exists(refresh_key)
        
        if not exists:
            # Key expired or doesn't exist - apply refresh
            if wallet.needs_daily_refresh():
                amount_added = wallet.apply_daily_refresh()
                
                if amount_added > 0:
                    # Create transaction record
                    transaction = TransactionHistory(
                        user_id=user_id,
                        transaction_type="daily_refresh",
                        amount=amount_added,
                        balance_after=wallet.total_credits,
                        description="Daily free credits refresh",
                        metadata={
                            "refresh_date": datetime.utcnow().isoformat(),
                        }
                    )
                    db.add(transaction)
                    
                    # Set TTL key for 24 hours
                    await self.redis.setex(refresh_key, 86400, "1")
                    
                    logger.info(f"Applied daily refresh for user {user_id}: {amount_added} credits")
                    
                    return amount_added
        
        return 0.0


# ==========================================
# Implementation Option 3: Cron Job
# ==========================================

"""
# Create a script: scripts/daily_refresh.py

import asyncio
import sys
sys.path.insert(0, '/path/to/your/project')

from app.services.daily_refresh_service import DailyRefreshService
from app.core.database import get_db_session

async def main():
    service = DailyRefreshService(get_db_session)
    stats = await service.refresh_all_users()
    print(f"Refresh completed: {stats}")

if __name__ == "__main__":
    asyncio.run(main())

# Add to crontab:
# 0 0 * * * /usr/bin/python3 /path/to/scripts/daily_refresh.py >> /var/log/daily_refresh.log 2>&1
"""


# ==========================================
# FastAPI Endpoint (Optional)
# ==========================================

"""
# In your API router

from fastapi import APIRouter, Depends
from app.services.daily_refresh_service import DailyRefreshService
from app.middleware.billing_middleware import get_billing_context, BillingContext

router = APIRouter()

@router.post("/wallet/refresh")
async def trigger_manual_refresh(
    billing: BillingContext = Depends(get_billing_context),
    db: AsyncSession = Depends(get_db_session)
):
    '''
    Manually trigger daily refresh for the authenticated user.
    '''
    service = DailyRefreshService(lambda: db)
    result = await service.refresh_user(billing.user_id)
    return result
"""
