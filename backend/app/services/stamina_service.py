"""
Stamina Service - 体力系统服务
==============================

管理用户聊天体力：
- 每天免费 50 条对话（F2P 友好）
- 体力不够时用月石购买
- 每日 0 点 UTC 重置体力

Author: Claude
Date: February 2025
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# Mock storage for demo/test users
_MOCK_STAMINA: Dict[str, Dict[str, Any]] = {}

# 常量
DAILY_FREE_STAMINA = 50
STAMINA_COST_PER_MESSAGE = 1
STAMINA_PURCHASE_PRICE = 10   # 10 月石
STAMINA_PURCHASE_AMOUNT = 10  # 获得 10 体力


class StaminaService:
    """
    体力服务
    
    提供:
    - get_stamina(user_id): 获取当前体力状态
    - consume_stamina(user_id, amount): 消耗体力
    - buy_stamina(user_id, amount): 用月石购买体力
    - daily_reset(user_id): 每日重置（自动在 get/consume 时检查）
    """
    
    async def get_stamina(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户体力状态
        
        自动检查并应用每日重置。
        
        Args:
            user_id: 用户ID
            
        Returns:
            {
                "current_stamina": int,
                "max_stamina": int,
                "last_reset_at": str (ISO format),
                "needs_purchase": bool
            }
        """
        if MOCK_MODE or user_id.startswith("demo"):
            return await self._get_stamina_mock(user_id)
        
        return await self._get_stamina_db(user_id)
    
    async def consume_stamina(self, user_id: str, amount: int = 1) -> Dict[str, Any]:
        """
        消耗体力
        
        Args:
            user_id: 用户ID
            amount: 消耗数量（默认 1）
            
        Returns:
            {
                "success": bool,
                "current_stamina": int,
                "consumed": int,
                "error": str (if failed)
            }
        """
        if amount <= 0:
            return {"success": True, "current_stamina": 0, "consumed": 0}
        
        if MOCK_MODE or user_id.startswith("demo"):
            return await self._consume_stamina_mock(user_id, amount)
        
        return await self._consume_stamina_db(user_id, amount)
    
    async def buy_stamina(self, user_id: str, packs: int = 1) -> Dict[str, Any]:
        """
        用月石购买体力
        
        Args:
            user_id: 用户ID
            packs: 购买包数（每包 10 月石 = 10 体力）
            
        Returns:
            {
                "success": bool,
                "stamina_added": int,
                "moonstone_spent": int,
                "current_stamina": int,
                "moonstone_balance": float,
                "error": str (if failed)
            }
        """
        if packs <= 0:
            return {"success": False, "error": "购买数量必须大于 0"}
        
        moonstone_cost = packs * STAMINA_PURCHASE_PRICE
        stamina_gain = packs * STAMINA_PURCHASE_AMOUNT
        
        if MOCK_MODE or user_id.startswith("demo"):
            return await self._buy_stamina_mock(user_id, moonstone_cost, stamina_gain)
        
        return await self._buy_stamina_db(user_id, moonstone_cost, stamina_gain)
    
    # ==================== Mock implementations ====================
    
    async def _get_stamina_mock(self, user_id: str) -> Dict[str, Any]:
        """Mock: 获取体力"""
        if user_id not in _MOCK_STAMINA:
            _MOCK_STAMINA[user_id] = {
                "current_stamina": DAILY_FREE_STAMINA,
                "max_stamina": DAILY_FREE_STAMINA,
                "last_reset_at": datetime.utcnow(),
            }
            logger.debug(f"[MOCK] Created stamina for {user_id}")
        
        stamina = _MOCK_STAMINA[user_id]
        
        # 检查每日重置
        last_reset = stamina["last_reset_at"]
        now = datetime.utcnow()
        if now.date() > last_reset.date():
            stamina["current_stamina"] = stamina["max_stamina"]
            stamina["last_reset_at"] = now
            logger.info(f"[MOCK] Daily reset for {user_id}")
        
        return {
            "current_stamina": stamina["current_stamina"],
            "max_stamina": stamina["max_stamina"],
            "last_reset_at": stamina["last_reset_at"].isoformat(),
            "needs_purchase": stamina["current_stamina"] <= 0,
        }
    
    async def _consume_stamina_mock(self, user_id: str, amount: int) -> Dict[str, Any]:
        """Mock: 消耗体力"""
        # 先获取（确保初始化 + 每日重置）
        await self._get_stamina_mock(user_id)
        stamina = _MOCK_STAMINA[user_id]
        
        if stamina["current_stamina"] < amount:
            return {
                "success": False,
                "current_stamina": stamina["current_stamina"],
                "consumed": 0,
                "error": f"体力不足：当前 {stamina['current_stamina']}，需要 {amount}",
            }
        
        stamina["current_stamina"] -= amount
        logger.info(f"[MOCK] Consumed {amount} stamina for {user_id}, remaining: {stamina['current_stamina']}")
        
        return {
            "success": True,
            "current_stamina": stamina["current_stamina"],
            "consumed": amount,
        }
    
    async def _buy_stamina_mock(self, user_id: str, moonstone_cost: int, stamina_gain: int) -> Dict[str, Any]:
        """Mock: 购买体力"""
        from app.services.wallet_service import wallet_service
        
        # 检查月石余额
        balance = await wallet_service.get_balance(user_id)
        if balance < moonstone_cost:
            return {
                "success": False,
                "error": f"月石不足：当前 {balance:.0f}，需要 {moonstone_cost}",
            }
        
        # 扣除月石
        deducted = await wallet_service.deduct(user_id, moonstone_cost, f"stamina_purchase:{stamina_gain}")
        if not deducted:
            return {
                "success": False,
                "error": "月石扣除失败",
            }
        
        # 增加体力
        await self._get_stamina_mock(user_id)  # 确保初始化
        _MOCK_STAMINA[user_id]["current_stamina"] += stamina_gain
        
        new_balance = await wallet_service.get_balance(user_id)
        
        logger.info(f"[MOCK] User {user_id} bought {stamina_gain} stamina for {moonstone_cost} moonstone")
        
        return {
            "success": True,
            "stamina_added": stamina_gain,
            "moonstone_spent": moonstone_cost,
            "current_stamina": _MOCK_STAMINA[user_id]["current_stamina"],
            "moonstone_balance": new_balance,
        }
    
    # ==================== Database implementations ====================
    
    async def _get_stamina_db(self, user_id: str) -> Dict[str, Any]:
        """DB: 获取体力"""
        from app.core.database import get_db
        from app.models.database.stamina_models import UserStamina
        from sqlalchemy import select
        
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(UserStamina).where(UserStamina.user_id == user_id)
                )
                stamina = result.scalar_one_or_none()
                
                if not stamina:
                    # 创建新用户的体力记录
                    stamina = UserStamina(
                        id=str(uuid4()),
                        user_id=user_id,
                        current_stamina=DAILY_FREE_STAMINA,
                        max_stamina=DAILY_FREE_STAMINA,
                        last_reset_at=datetime.utcnow(),
                    )
                    session.add(stamina)
                    await session.commit()
                    logger.info(f"Created stamina record for user: {user_id}")
                else:
                    # 检查每日重置
                    if stamina.needs_daily_reset():
                        stamina.apply_daily_reset()
                        await session.commit()
                        logger.info(f"Daily reset applied for user: {user_id}")
                
                return {
                    "current_stamina": stamina.current_stamina,
                    "max_stamina": stamina.max_stamina,
                    "last_reset_at": stamina.last_reset_at.isoformat(),
                    "needs_purchase": stamina.current_stamina <= 0,
                }
                
        except Exception as e:
            logger.error(f"Error getting stamina for {user_id}: {e}")
            # Fallback to mock
            return await self._get_stamina_mock(user_id)
    
    async def _consume_stamina_db(self, user_id: str, amount: int) -> Dict[str, Any]:
        """DB: 消耗体力"""
        from app.core.database import get_db
        from app.models.database.stamina_models import UserStamina
        from sqlalchemy import select
        
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(UserStamina)
                    .where(UserStamina.user_id == user_id)
                    .with_for_update()
                )
                stamina = result.scalar_one_or_none()
                
                if not stamina:
                    # 创建新记录
                    stamina = UserStamina(
                        id=str(uuid4()),
                        user_id=user_id,
                        current_stamina=DAILY_FREE_STAMINA,
                        max_stamina=DAILY_FREE_STAMINA,
                        last_reset_at=datetime.utcnow(),
                    )
                    session.add(stamina)
                
                # 检查每日重置
                if stamina.needs_daily_reset():
                    stamina.apply_daily_reset()
                
                # 检查体力是否足够
                if stamina.current_stamina < amount:
                    return {
                        "success": False,
                        "current_stamina": stamina.current_stamina,
                        "consumed": 0,
                        "error": f"体力不足：当前 {stamina.current_stamina}，需要 {amount}",
                    }
                
                # 扣除体力
                stamina.current_stamina -= amount
                stamina.updated_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"Consumed {amount} stamina for {user_id}, remaining: {stamina.current_stamina}")
                
                return {
                    "success": True,
                    "current_stamina": stamina.current_stamina,
                    "consumed": amount,
                }
                
        except Exception as e:
            logger.error(f"Error consuming stamina for {user_id}: {e}")
            return {
                "success": False,
                "current_stamina": 0,
                "consumed": 0,
                "error": str(e),
            }
    
    async def _buy_stamina_db(self, user_id: str, moonstone_cost: int, stamina_gain: int) -> Dict[str, Any]:
        """DB: 购买体力"""
        from app.core.database import get_db
        from app.services.wallet_service import wallet_service
        from app.models.database.stamina_models import UserStamina
        from app.models.database.billing_models import TransactionHistory, TransactionType
        from sqlalchemy import select
        
        try:
            # 先检查月石余额
            balance = await wallet_service.get_balance(user_id)
            if balance < moonstone_cost:
                return {
                    "success": False,
                    "error": f"月石不足：当前 {balance:.0f}，需要 {moonstone_cost}",
                }
            
            # 扣除月石（wallet_service 会记录 transaction）
            deducted = await wallet_service.deduct(
                user_id, 
                moonstone_cost, 
                f"stamina_purchase:{stamina_gain}"
            )
            if not deducted:
                return {
                    "success": False,
                    "error": "月石扣除失败",
                }
            
            # 增加体力
            async with get_db() as session:
                result = await session.execute(
                    select(UserStamina)
                    .where(UserStamina.user_id == user_id)
                    .with_for_update()
                )
                stamina = result.scalar_one_or_none()
                
                if not stamina:
                    stamina = UserStamina(
                        id=str(uuid4()),
                        user_id=user_id,
                        current_stamina=DAILY_FREE_STAMINA + stamina_gain,
                        max_stamina=DAILY_FREE_STAMINA,
                        last_reset_at=datetime.utcnow(),
                    )
                    session.add(stamina)
                else:
                    stamina.current_stamina += stamina_gain
                    stamina.updated_at = datetime.utcnow()
                
                await session.commit()
                
                new_balance = await wallet_service.get_balance(user_id)
                
                logger.info(f"User {user_id} bought {stamina_gain} stamina for {moonstone_cost} moonstone")
                
                return {
                    "success": True,
                    "stamina_added": stamina_gain,
                    "moonstone_spent": moonstone_cost,
                    "current_stamina": stamina.current_stamina,
                    "moonstone_balance": new_balance,
                }
                
        except Exception as e:
            logger.error(f"Error buying stamina for {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Singleton instance
stamina_service = StaminaService()
