"""
Wallet Service - Credit management for user wallets
==================================================

提供用户钱包的余额查询和扣费功能。

Author: Claude
Date: February 2025
"""

import os
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# Mock storage for demo users
_MOCK_WALLETS: dict[str, float] = {}
DEFAULT_MOCK_BALANCE = 1000.0  # Demo users get 1000 credits


class WalletService:
    """
    钱包服务 - 管理用户金币/月石余额
    
    支持:
    - get_balance(user_id): 获取余额
    - deduct(user_id, amount, reason): 扣除金币
    - add_credits(user_id, amount, reason): 增加金币
    """
    
    async def get_balance(self, user_id: str) -> float:
        """获取用户余额"""
        if MOCK_MODE or user_id.startswith("demo"):
            # Mock mode or demo user
            if user_id not in _MOCK_WALLETS:
                _MOCK_WALLETS[user_id] = DEFAULT_MOCK_BALANCE
                logger.debug(f"[MOCK] Created wallet for {user_id} with {DEFAULT_MOCK_BALANCE} credits")
            return _MOCK_WALLETS[user_id]
        
        # Real database query
        try:
            from app.core.database import get_db
            from app.models.database.billing_models import UserWallet
            from sqlalchemy import select
            
            async with get_db() as session:
                result = await session.execute(
                    select(UserWallet).where(UserWallet.user_id == user_id)
                )
                wallet = result.scalar_one_or_none()
                
                if wallet:
                    return wallet.total_credits
                else:
                    # Create wallet for new user
                    logger.info(f"Creating wallet for new user: {user_id}")
                    new_wallet = UserWallet(
                        wallet_id=str(uuid4()),
                        user_id=user_id,
                        free_credits=10.0,
                        purchased_credits=0.0,
                        total_credits=10.0,
                    )
                    session.add(new_wallet)
                    await session.commit()
                    return new_wallet.total_credits
                    
        except Exception as e:
            logger.error(f"Error getting balance for {user_id}: {e}")
            # Fallback to mock mode on error
            if user_id not in _MOCK_WALLETS:
                _MOCK_WALLETS[user_id] = DEFAULT_MOCK_BALANCE
            return _MOCK_WALLETS[user_id]
    
    async def deduct(self, user_id: str, amount: float, reason: str = "") -> bool:
        """
        扣除用户金币
        
        Args:
            user_id: 用户ID
            amount: 扣除金额
            reason: 扣费原因 (e.g., "photo:character_id", "dressup:character_id")
            
        Returns:
            bool: 是否扣费成功
        """
        if amount <= 0:
            return True
            
        if MOCK_MODE or user_id.startswith("demo"):
            # Mock mode or demo user
            if user_id not in _MOCK_WALLETS:
                _MOCK_WALLETS[user_id] = DEFAULT_MOCK_BALANCE
            
            if _MOCK_WALLETS[user_id] < amount:
                logger.warning(f"[MOCK] Insufficient credits for {user_id}: {_MOCK_WALLETS[user_id]} < {amount}")
                return False
            
            _MOCK_WALLETS[user_id] -= amount
            logger.info(f"[MOCK] Deducted {amount} from {user_id} for {reason}, new balance: {_MOCK_WALLETS[user_id]}")
            return True
        
        # Real database transaction
        try:
            from app.core.database import get_db
            from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
            from sqlalchemy import select
            
            async with get_db() as session:
                # Lock the wallet row for update
                result = await session.execute(
                    select(UserWallet)
                    .where(UserWallet.user_id == user_id)
                    .with_for_update()
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    logger.error(f"Wallet not found for user: {user_id}")
                    return False
                
                if wallet.total_credits < amount:
                    logger.warning(f"Insufficient credits for {user_id}: {wallet.total_credits} < {amount}")
                    return False
                
                # Deduct from purchased first, then free
                if wallet.purchased_credits >= amount:
                    wallet.purchased_credits -= amount
                else:
                    remaining = amount - wallet.purchased_credits
                    wallet.purchased_credits = 0.0
                    wallet.free_credits = max(0, wallet.free_credits - remaining)
                
                wallet.total_credits = wallet.free_credits + wallet.purchased_credits
                wallet.updated_at = datetime.utcnow()
                
                # Record transaction
                transaction = TransactionHistory(
                    transaction_id=str(uuid4()),
                    user_id=user_id,
                    transaction_type=TransactionType.DEDUCTION,
                    amount=-amount,
                    balance_after=wallet.total_credits,
                    description=reason,
                    extra_data={"source": "wallet_service"},
                )
                session.add(transaction)
                
                await session.commit()
                logger.info(f"Deducted {amount} from {user_id} for {reason}, new balance: {wallet.total_credits}")
                return True
                
        except Exception as e:
            logger.error(f"Error deducting credits for {user_id}: {e}")
            return False
    
    async def add_credits(self, user_id: str, amount: float, reason: str = "", is_purchased: bool = False) -> bool:
        """
        增加用户金币
        
        Args:
            user_id: 用户ID
            amount: 增加金额
            reason: 原因
            is_purchased: 是否是购买的金币
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
            
        if MOCK_MODE or user_id.startswith("demo"):
            if user_id not in _MOCK_WALLETS:
                _MOCK_WALLETS[user_id] = DEFAULT_MOCK_BALANCE
            _MOCK_WALLETS[user_id] += amount
            logger.info(f"[MOCK] Added {amount} to {user_id} for {reason}, new balance: {_MOCK_WALLETS[user_id]}")
            return True
        
        try:
            from app.core.database import get_db
            from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
            from sqlalchemy import select
            
            async with get_db() as session:
                result = await session.execute(
                    select(UserWallet)
                    .where(UserWallet.user_id == user_id)
                    .with_for_update()
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    logger.error(f"Wallet not found for user: {user_id}")
                    return False
                
                if is_purchased:
                    wallet.purchased_credits += amount
                else:
                    wallet.free_credits += amount
                
                wallet.total_credits = wallet.free_credits + wallet.purchased_credits
                wallet.updated_at = datetime.utcnow()
                
                # Record transaction
                transaction = TransactionHistory(
                    transaction_id=str(uuid4()),
                    user_id=user_id,
                    transaction_type=TransactionType.PURCHASE if is_purchased else TransactionType.BONUS,
                    amount=amount,
                    balance_after=wallet.total_credits,
                    description=reason,
                )
                session.add(transaction)
                
                await session.commit()
                logger.info(f"Added {amount} to {user_id} for {reason}, new balance: {wallet.total_credits}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding credits for {user_id}: {e}")
            return False


# Singleton instance
wallet_service = WalletService()
