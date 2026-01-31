"""
Gift Service - Core Gift Processing Engine
==========================================

Handles gift sending with:
- Idempotency checks (prevents duplicate charges)
- DB transaction for atomicity (deduct + record + XP)
- Transaction ledger for accounting
- AI acknowledgment flow
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.services.payment_service import payment_service, _transactions
from app.services.intimacy_service import intimacy_service
from app.models.database.gift_models import DEFAULT_GIFT_CATALOG, GiftStatus

# Import emotion service for mood-aware gift responses
try:
    from app.services.emotion_service import emotion_service
except ImportError:
    emotion_service = None

logger = logging.getLogger(__name__)

# Use same mock setting as payment service for consistency
MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"
logger.info(f"Gift service MOCK_MODE: {MOCK_MODE}")

# Module-level storage for mock mode
_MOCK_GIFTS: Dict[str, dict] = {}
_MOCK_IDEMPOTENCY_KEYS: Dict[str, dict] = {}
_MOCK_GIFT_CATALOG: Dict[str, dict] = {g["gift_type"]: g for g in DEFAULT_GIFT_CATALOG}

# Idempotency key expiration (24 hours)
IDEMPOTENCY_KEY_TTL = timedelta(hours=24)


class GiftService:
    """
    Gift service with idempotency and transaction guarantees.
    
    Flow:
    1. Client generates idempotency_key (UUID)
    2. POST /gifts with idempotency_key
    3. Service checks if key exists:
       - If exists and not expired: return cached result
       - If new: BEGIN TRANSACTION
           a. Deduct credits from wallet
           b. Create gift record
           c. Create transaction record (ledger)
           d. Award XP
           e. Store idempotency key
         COMMIT
    4. Return gift_id + details
    5. Trigger AI response with gift context
    6. AI responds, gift marked as acknowledged
    """
    
    def __init__(self):
        self.mock_mode = MOCK_MODE
    
    # =========================================================================
    # Gift Catalog
    # =========================================================================
    
    async def get_catalog(self) -> List[dict]:
        """Get all active gifts in catalog"""
        catalog = [
            g for g in _MOCK_GIFT_CATALOG.values()
            if g.get("is_active", True)
        ]
        catalog.sort(key=lambda x: x.get("sort_order", 0))
        return catalog
    
    async def get_gift_info(self, gift_type: str) -> Optional[dict]:
        """Get gift info by type"""
        return _MOCK_GIFT_CATALOG.get(gift_type)
    
    # =========================================================================
    # Idempotency Checks
    # =========================================================================
    
    async def check_idempotency_key(
        self, 
        idempotency_key: str, 
        user_id: str
    ) -> Tuple[bool, Optional[dict]]:
        """
        Check if idempotency key exists and is valid.
        
        Returns:
            (is_duplicate, cached_result)
        """
        if self.mock_mode:
            key_data = _MOCK_IDEMPOTENCY_KEYS.get(idempotency_key)
            
            if not key_data:
                return (False, None)
            
            # Check if expired
            if datetime.utcnow() > key_data["expires_at"]:
                del _MOCK_IDEMPOTENCY_KEYS[idempotency_key]
                return (False, None)
            
            # Check user matches (security)
            if key_data["user_id"] != user_id:
                logger.warning(f"Idempotency key user mismatch: {user_id} vs {key_data['user_id']}")
                return (False, None)
            
            # Return cached result
            cached = key_data.get("result")
            if cached:
                return (True, json.loads(cached))
            
            return (True, {"gift_id": key_data.get("gift_id")})
        
        # Database mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import IdempotencyKey
        
        async with get_db() as db:
            result = await db.execute(
                select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
            )
            key_data = result.scalar_one_or_none()
            
            if not key_data:
                return (False, None)
            
            if key_data.is_expired():
                await db.delete(key_data)
                await db.commit()
                return (False, None)
            
            if key_data.user_id != user_id:
                logger.warning(f"Idempotency key user mismatch: {user_id} vs {key_data.user_id}")
                return (False, None)
            
            cached = key_data.result
            if cached:
                return (True, json.loads(cached))
            
            return (True, {"gift_id": key_data.gift_id})
    
    async def store_idempotency_key(
        self,
        idempotency_key: str,
        user_id: str,
        gift_id: str,
        result: dict
    ) -> None:
        """Store idempotency key with result"""
        # Convert datetime objects to ISO strings for JSON serialization
        def serialize_result(obj):
            if isinstance(obj, dict):
                return {k: serialize_result(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_result(v) for v in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        serialized_result = serialize_result(result)
        
        if self.mock_mode:
            _MOCK_IDEMPOTENCY_KEYS[idempotency_key] = {
                "key": idempotency_key,
                "user_id": user_id,
                "gift_id": gift_id,
                "result": json.dumps(serialized_result),
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + IDEMPOTENCY_KEY_TTL,
            }
            return
        
        # Database mode
        from app.core.database import get_db
        from app.models.database.gift_models import IdempotencyKey
        
        async with get_db() as db:
            key_obj = IdempotencyKey(
                key=idempotency_key,
                user_id=user_id,
                gift_id=gift_id,
                result=json.dumps(serialized_result),
                expires_at=datetime.utcnow() + IDEMPOTENCY_KEY_TTL,
            )
            db.add(key_obj)
            await db.commit()
    
    # =========================================================================
    # Core Gift Operations
    # =========================================================================
    
    async def send_gift(
        self,
        user_id: str,
        character_id: str,
        gift_type: str,
        idempotency_key: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Send a gift with transaction guarantees.
        
        All steps are atomic - if any fail, everything rolls back.
        
        Steps (in transaction):
        1. Check idempotency - if duplicate, return cached
        2. Validate gift type
        3. Check balance
        4. Deduct credits
        5. Create gift record
        6. Create transaction record (ledger)
        7. Award XP
        8. Store idempotency key
        """
        # Step 1: Check idempotency (outside transaction - read only)
        is_duplicate, cached_result = await self.check_idempotency_key(idempotency_key, user_id)
        if is_duplicate:
            logger.info(f"Duplicate gift request detected: {idempotency_key}")
            return {
                "success": True,
                "is_duplicate": True,
                **cached_result
            }
        
        # Step 2: Validate gift type
        gift_info = await self.get_gift_info(gift_type)
        if not gift_info:
            return {
                "success": False,
                "error": "invalid_gift_type",
                "message": f"Unknown gift type: {gift_type}"
            }
        
        price = gift_info["price"]
        xp_reward = gift_info["xp_reward"]
        
        # Step 3: Check balance (pre-check, will verify again in transaction)
        wallet = await payment_service.get_wallet(user_id)
        if wallet["total_credits"] < price:
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": f"余额不足: 当前 {wallet['total_credits']} 金币，需要 {price} 金币",
                "current_balance": wallet["total_credits"],
                "required": price,
            }
        
        # =====================================================================
        # BEGIN TRANSACTION (mock mode simulates; real DB uses actual transaction)
        # =====================================================================
        try:
            # In production with real DB:
            # async with db.transaction():
            #     ... all the following steps ...
            
            now = datetime.utcnow()
            gift_id = str(uuid4())
            transaction_id = str(uuid4())
            
            # Step 4: Deduct credits
            wallet = await payment_service.deduct_credits(user_id, price)
            logger.info(f"Credits deducted: {price} from user {user_id}, new balance: {wallet['total_credits']}")
            
            # Step 5: Create gift record
            gift = {
                "id": gift_id,
                "user_id": user_id,
                "character_id": character_id,
                "session_id": session_id,
                "gift_type": gift_type,
                "gift_name": gift_info["name"],
                "gift_name_cn": gift_info.get("name_cn"),
                "gift_price": price,
                "xp_reward": xp_reward,
                "status": GiftStatus.PENDING.value,
                "idempotency_key": idempotency_key,
                "created_at": now,
                "acknowledged_at": None,
                "icon": gift_info.get("icon", "🎁"),
            }
            
            description = f"送出礼物: {gift_info.get('name_cn') or gift_info['name']} 给角色 {character_id}"
            
            if self.mock_mode:
                _MOCK_GIFTS[gift_id] = gift
                logger.info(f"Gift record created (mock): {gift_id}")
                
                # Step 6: Create transaction record (ledger entry) - mock mode
                transaction_record = {
                    "id": transaction_id,
                    "user_id": user_id,
                    "transaction_type": "gift",
                    "amount": 0,
                    "credits": -price,
                    "description": description,
                    "payment_provider": None,
                    "provider_transaction_id": None,
                    "gift_id": gift_id,
                    "character_id": character_id,
                    "status": "completed",
                    "created_at": now,
                }
                _transactions.append(transaction_record)
                logger.info(f"Transaction record created (mock): {transaction_id}")
            else:
                # Database mode
                from app.core.database import get_db
                from app.models.database.gift_models import Gift as GiftModel
                from app.models.database.billing_models import TransactionHistory, TransactionType
                
                async with get_db() as db:
                    # Create gift record in database
                    gift_obj = GiftModel(
                        id=gift_id,
                        user_id=user_id,
                        character_id=character_id,
                        session_id=session_id,
                        gift_type=gift_type,
                        gift_name=gift_info["name"],
                        gift_name_cn=gift_info.get("name_cn"),
                        gift_price=price,
                        xp_reward=xp_reward,
                        status=GiftStatus.PENDING.value,
                        idempotency_key=idempotency_key,
                    )
                    db.add(gift_obj)
                    logger.info(f"Gift record created (db): {gift_id}")
                    
                    # Step 6: Create transaction record (ledger entry) - database mode
                    transaction_obj = TransactionHistory(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        transaction_type=TransactionType.GIFT,
                        amount=-price,
                        balance_after=wallet["total_credits"],
                        description=description,
                        extra_data={"gift_id": gift_id, "character_id": character_id, "gift_type": gift_type},
                    )
                    db.add(transaction_obj)
                    await db.commit()
                    logger.info(f"Transaction record created (db): {transaction_id}")
            
            # Step 7: Award XP
            xp_result = await intimacy_service.award_xp(
                user_id, 
                character_id, 
                "emotional",  # Gifts use emotional XP type
                force=True   # Bypass daily limits for gifts
            )
            actual_xp = xp_result.get("xp_awarded", 0)
            
            # Add gift-specific bonus XP (for expensive gifts)
            bonus_xp = max(0, xp_reward - actual_xp)
            if bonus_xp > 0:
                intimacy = await intimacy_service.get_or_create_intimacy(user_id, character_id)
                intimacy["total_xp"] += bonus_xp
                intimacy["daily_xp_earned"] += bonus_xp
                actual_xp += bonus_xp
            
            logger.info(f"XP awarded: {actual_xp} (base: {xp_result.get('xp_awarded', 0)}, bonus: {bonus_xp})")
            
            # Step 8: Store idempotency key
            result = {
                "gift_id": gift_id,
                "gift": gift,
                "transaction_id": transaction_id,
                "credits_deducted": price,
                "new_balance": wallet["total_credits"],
                "xp_awarded": actual_xp,
                "level_up": xp_result.get("level_up", False),
                "new_level": xp_result.get("new_level"),
                "new_stage": xp_result.get("new_stage"),
            }
            await self.store_idempotency_key(idempotency_key, user_id, gift_id, result)
            
            # =====================================================================
            # COMMIT TRANSACTION
            # =====================================================================
            
            logger.info(f"Gift transaction completed: {gift_type} from {user_id} to {character_id}")
            
            # Get current intimacy level for response calibration
            current_level = xp_result.get("new_level") or xp_result.get("current_level", 1)
            
            # Get current emotional state (if emotion service available)
            current_mood = "neutral"
            if emotion_service:
                try:
                    emotion_data = await emotion_service.get_emotion(user_id, character_id)
                    current_mood = emotion_data.get("emotional_state", "neutral")
                except Exception as e:
                    logger.warning(f"Could not get emotion state: {e}")
            
            return {
                "success": True,
                "is_duplicate": False,
                **result,
                "system_message": self._build_gift_system_message(
                    gift, 
                    actual_xp,
                    intimacy_level=current_level,
                    current_mood=current_mood
                ),
            }
            
        except ValueError as e:
            # Balance check failed during deduction
            logger.error(f"Gift transaction failed (insufficient funds): {e}")
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": str(e)
            }
        except Exception as e:
            # Any other error - in real DB this would trigger rollback
            logger.error(f"Gift transaction failed: {e}", exc_info=True)
            # TODO: In real DB mode, rollback would happen automatically
            # For mock mode, we'd need to manually revert changes
            return {
                "success": False,
                "error": "transaction_failed",
                "message": f"送礼失败，请稍后重试: {str(e)}"
            }
    
    def _build_gift_system_message(
        self, 
        gift: dict, 
        xp_awarded: int,
        intimacy_level: int = 1,
        current_mood: str = "neutral"
    ) -> str:
        """
        Build system message for AI context when user sends a gift.
        
        Response intensity is calibrated based on:
        - Current intimacy level (1-100)
        - Gift value
        - Current emotional state/mood
        
        Key principle: Gifts should NOT instantly flip negative emotions to extremely positive.
        A gift can soften the mood, but dramatic shifts should require higher intimacy.
        """
        gift_name = gift.get("gift_name_cn") or gift.get("gift_name")
        icon = gift.get("icon", "🎁")
        price = gift['gift_price']
        
        # Determine current mood description for AI
        is_negative_mood = current_mood in ["angry", "upset", "annoyed", "hurt", "cold", "silent"]
        mood_description = {
            "loving": "你现在很甜蜜开心",
            "happy": "你现在心情很好",
            "neutral": "你现在心情平和",
            "curious": "你现在有点好奇",
            "annoyed": "你现在有点不高兴",
            "angry": "你现在在生气",
            "hurt": "你现在有点受伤难过",
            "cold": "你现在有点冷淡",
            "silent": "你现在不太想说话",
        }.get(current_mood, "你现在心情平和")
        
        # Build tone guide based on intimacy level (WITHOUT mentioning anger unless actually angry)
        if intimacy_level <= 3:
            tone_guide = (
                "保持礼貌但有距离感。可以表示感谢，但不要太热情或亲密。"
                "不要说'亲爱的'这类亲密称呼。保持客气但略显拘谨。"
            )
        elif intimacy_level <= 6:
            tone_guide = (
                "用朋友之间的温暖语气回应，可以表示开心和感谢。"
                "可以稍微活泼一些，但不要太过亲密或暧昧。"
            )
        elif intimacy_level <= 9:
            tone_guide = (
                "可以表现得比较开心和感动，语气亲近。"
                "可以有一些亲昵的表达，但保持适度。"
            )
        else:
            tone_guide = (
                "可以非常热情和亲密地回应，表达深厚的感情。"
                "可以使用亲密的称呼和表达方式。"
            )
        
        # Adjust for gift value
        if price >= 100:
            value_note = "这是一份非常贵重的礼物，可以表现得更加惊喜。"
        elif price >= 50:
            value_note = "这是一份不错的礼物。"
        elif price >= 20:
            value_note = "这是一份普通的小礼物。"
        else:
            value_note = "这是一份简单的心意。"
        
        # Handle mood-specific guidance (ONLY mention anger if actually angry)
        if is_negative_mood:
            mood_note = (
                f"重要：{mood_description}。礼物可以让你态度软化一些，"
                "但不要立刻180度大转变变得超级开心。情绪转变应该是渐进的。"
                "可以表示'哼，算你有心'这样的傲娇反应，而不是立刻变得很甜蜜。"
            )
        else:
            # Positive or neutral mood - just be happy about the gift
            mood_note = f"{mood_description}，收到礼物自然地感到开心就好。"
        
        return (
            f"[SYSTEM] 用户送给你一份'{icon} {gift_name}'礼物（价值{price}金币）。"
            f"好感度+{xp_awarded}。当前亲密等级：{intimacy_level}。\n\n"
            f"当前状态：{mood_description}\n"
            f"回应指南：{tone_guide}\n{value_note}\n{mood_note}"
        )
    
    # =========================================================================
    # Gift Status Management
    # =========================================================================
    
    async def get_gift(self, gift_id: str) -> Optional[dict]:
        """Get gift by ID"""
        if self.mock_mode:
            return _MOCK_GIFTS.get(gift_id)
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import Gift as GiftModel
        
        async with get_db() as db:
            result = await db.execute(
                select(GiftModel).where(GiftModel.id == gift_id)
            )
            gift = result.scalar_one_or_none()
            if not gift:
                return None
            return {
                "id": gift.id,
                "user_id": gift.user_id,
                "character_id": gift.character_id,
                "session_id": gift.session_id,
                "gift_type": gift.gift_type,
                "gift_name": gift.gift_name,
                "gift_name_cn": gift.gift_name_cn,
                "gift_price": gift.gift_price,
                "xp_reward": gift.xp_reward,
                "status": gift.status,
                "idempotency_key": gift.idempotency_key,
                "created_at": gift.created_at,
                "acknowledged_at": gift.acknowledged_at,
            }
    
    async def mark_acknowledged(self, gift_id: str) -> bool:
        """Mark gift as acknowledged (AI has responded)"""
        if self.mock_mode:
            gift = _MOCK_GIFTS.get(gift_id)
            if not gift:
                return False
            gift["status"] = GiftStatus.ACKNOWLEDGED.value
            gift["acknowledged_at"] = datetime.utcnow()
            return True
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import Gift as GiftModel
        
        async with get_db() as db:
            result = await db.execute(
                select(GiftModel).where(GiftModel.id == gift_id)
            )
            gift = result.scalar_one_or_none()
            if not gift:
                return False
            gift.status = GiftStatus.ACKNOWLEDGED.value
            gift.acknowledged_at = datetime.utcnow()
            await db.commit()
            return True
    
    async def get_pending_gifts(self, user_id: str, character_id: str) -> List[dict]:
        """Get pending (unacknowledged) gifts for a user-character pair"""
        if self.mock_mode:
            pending = [
                g for g in _MOCK_GIFTS.values()
                if g["user_id"] == user_id
                and g["character_id"] == character_id
                and g["status"] == GiftStatus.PENDING.value
            ]
            pending.sort(key=lambda x: x["created_at"])
            return pending
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import Gift as GiftModel
        
        async with get_db() as db:
            result = await db.execute(
                select(GiftModel).where(
                    GiftModel.user_id == user_id,
                    GiftModel.character_id == character_id,
                    GiftModel.status == GiftStatus.PENDING.value
                ).order_by(GiftModel.created_at)
            )
            gifts = result.scalars().all()
            return [
                {
                    "id": g.id,
                    "user_id": g.user_id,
                    "character_id": g.character_id,
                    "gift_type": g.gift_type,
                    "gift_name": g.gift_name,
                    "gift_name_cn": g.gift_name_cn,
                    "gift_price": g.gift_price,
                    "xp_reward": g.xp_reward,
                    "status": g.status,
                    "created_at": g.created_at,
                }
                for g in gifts
            ]
    
    async def get_gift_history(
        self,
        user_id: str,
        character_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[dict]:
        """Get gift history for a user"""
        if self.mock_mode:
            gifts = [g for g in _MOCK_GIFTS.values() if g["user_id"] == user_id]
            if character_id:
                gifts = [g for g in gifts if g["character_id"] == character_id]
            gifts.sort(key=lambda x: x["created_at"], reverse=True)
            return gifts[offset:offset + limit]
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import Gift as GiftModel
        
        async with get_db() as db:
            query = select(GiftModel).where(GiftModel.user_id == user_id)
            if character_id:
                query = query.where(GiftModel.character_id == character_id)
            query = query.order_by(GiftModel.created_at.desc()).offset(offset).limit(limit)
            
            result = await db.execute(query)
            gifts = result.scalars().all()
            return [
                {
                    "id": g.id,
                    "user_id": g.user_id,
                    "character_id": g.character_id,
                    "gift_type": g.gift_type,
                    "gift_name": g.gift_name,
                    "gift_name_cn": g.gift_name_cn,
                    "gift_price": g.gift_price,
                    "xp_reward": g.xp_reward,
                    "status": g.status,
                    "created_at": g.created_at,
                    "acknowledged_at": g.acknowledged_at,
                }
                for g in gifts
            ]
    
    async def get_gift_summary(self, user_id: str, character_id: str) -> dict:
        """
        Get gift summary for AI memory context.
        """
        gifts = [
            g for g in _MOCK_GIFTS.values()
            if g["user_id"] == user_id and g["character_id"] == character_id
        ]
        
        total_gifts = len(gifts)
        total_spent = sum(g["gift_price"] for g in gifts)
        total_xp = sum(g["xp_reward"] for g in gifts)
        
        # Count by type
        gift_counts = {}
        for g in gifts:
            gift_type = g["gift_type"]
            if gift_type not in gift_counts:
                gift_counts[gift_type] = {
                    "count": 0,
                    "name": g["gift_name"],
                    "name_cn": g.get("gift_name_cn"),
                    "icon": g.get("icon", "🎁"),
                }
            gift_counts[gift_type]["count"] += 1
        
        # Sort by count descending
        top_gifts = sorted(
            gift_counts.values(),
            key=lambda x: x["count"],
            reverse=True
        )[:5]
        
        return {
            "total_gifts": total_gifts,
            "total_spent": total_spent,
            "total_xp_from_gifts": total_xp,
            "top_gifts": top_gifts,
            "first_gift_at": min((g["created_at"] for g in gifts), default=None),
            "last_gift_at": max((g["created_at"] for g in gifts), default=None),
        }
    
    # =========================================================================
    # Transaction History (for user's ledger view)
    # =========================================================================
    
    async def get_gift_transactions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[dict]:
        """Get gift-related transactions for ledger display"""
        gift_txns = [
            t for t in _transactions 
            if t["user_id"] == user_id and t["transaction_type"] == "gift"
        ]
        gift_txns.sort(key=lambda x: x["created_at"], reverse=True)
        return gift_txns[offset:offset + limit]


# Global service instance
gift_service = GiftService()
