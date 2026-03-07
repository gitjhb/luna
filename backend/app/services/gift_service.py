"""
Gift Service - Core Gift Processing Engine
==========================================

Handles gift sending with:
- Idempotency checks (prevents duplicate charges)
- DB transaction for atomicity (deduct + record + XP)
- Transaction ledger for accounting
- Status effect application (Tier 2 gifts)
- AI acknowledgment flow

货币单位: 月石 (Moon Stones)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.services.payment_service import payment_service, _transactions
from app.services.intimacy_service import intimacy_service
from app.services.effect_service import effect_service
from app.models.database.gift_models import DEFAULT_GIFT_CATALOG, GiftStatus, GiftTier

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
           a. Deduct 月石 from wallet
           b. Create gift record
           c. Create transaction record (ledger)
           d. Award XP
           e. Apply status effect (if Tier 2)
           f. Store idempotency key
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
    
    async def get_catalog(self, tier: Optional[int] = None) -> List[dict]:
        """
        Get all active gifts in catalog.
        
        Args:
            tier: Optional tier filter (1-4)
        """
        catalog = [
            g for g in _MOCK_GIFT_CATALOG.values()
            if g.get("is_active", True) != False
        ]
        
        if tier is not None:
            catalog = [g for g in catalog if g.get("tier") == tier]
        
        catalog.sort(key=lambda x: x.get("sort_order", 0))
        return catalog
    
    async def get_catalog_by_tier(self) -> Dict[int, List[dict]]:
        """
        Get catalog organized by tier for UI display.
        """
        all_gifts = await self.get_catalog()
        
        by_tier = {
            GiftTier.CONSUMABLE: [],
            GiftTier.STATE_TRIGGER: [],
            GiftTier.SPEED_DATING: [],
            GiftTier.WHALE_BAIT: [],
        }
        
        for gift in all_gifts:
            tier = gift.get("tier", GiftTier.CONSUMABLE)
            if tier in by_tier:
                by_tier[tier].append(gift)
        
        return by_tier
    
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
        4. Deduct 月石
        5. Create gift record
        6. Create transaction record (ledger)
        7. Award XP
        8. Apply status effect (if Tier 2 gift)
        9. Store idempotency key
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
        
        # Validate character exclusive gifts
        if gift_info.get("character_exclusive"):
            required_character = gift_info["character_exclusive"]
            if character_id != required_character:
                char_name = gift_info.get("name_cn") or gift_info["name"]
                return {
                    "success": False,
                    "error": "character_exclusive",
                    "message": f"'{char_name}' 是角色专属礼物，只能送给对应角色",
                }

        # Validate min_stage for touch/interaction gifts
        if gift_info.get("min_stage"):
            required_stage = gift_info["min_stage"]
            stage_order = ["strangers", "friends", "ambiguous", "lovers", "soulmates"]
            intimacy_record = await intimacy_service.get_or_create_intimacy(user_id, character_id)
            current_stage = intimacy_record.get("intimacy_stage", "strangers")

            required_idx = stage_order.index(required_stage) if required_stage in stage_order else 0
            current_idx = stage_order.index(current_stage) if current_stage in stage_order else 0

            if current_idx < required_idx:
                stage_names_cn = {
                    "strangers": "陌生人", "friends": "朋友",
                    "ambiguous": "暧昧", "lovers": "恋人", "soulmates": "挚爱",
                }
                return {
                    "success": False,
                    "error": "stage_too_low",
                    "message": f"亲密度不足：需要达到'{stage_names_cn.get(required_stage, required_stage)}'阶段才能使用此礼物",
                }

        price = gift_info["price"]
        xp_reward = gift_info["xp_reward"]
        tier = gift_info.get("tier", GiftTier.CONSUMABLE)
        
        # Step 3: Check balance (pre-check, will verify again in transaction)
        wallet = await payment_service.get_wallet(user_id)
        if wallet["total_credits"] < price:
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": f"月石不足: 当前 {wallet['total_credits']} 月石，需要 {price} 月石",
                "current_balance": wallet["total_credits"],
                "required": price,
            }
        
        # =====================================================================
        # BEGIN TRANSACTION
        # =====================================================================
        try:
            now = datetime.utcnow()
            gift_id = str(uuid4())
            transaction_id = str(uuid4())
            
            # Step 4: Deduct 月石 (包含交易记录)
            gift_name = gift_info.get('name_cn') or gift_info['name']
            description = f"送出礼物: {gift_name} ({price} 月石)"
            wallet = await payment_service.deduct_credits(
                user_id, price, 
                description=description,
                extra_data={"gift_type": gift_type},
                transaction_type="gift"
            )
            logger.info(f"月石 deducted: {price} from user {user_id}, new balance: {wallet['total_credits']}")
            
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
                "tier": tier,
                "status": GiftStatus.PENDING.value,
                "idempotency_key": idempotency_key,
                "created_at": now,
                "acknowledged_at": None,
                "icon": gift_info.get("icon", "🎁"),
            }
            
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
                # TransactionHistory 已在 payment_service.deduct_credits 中创建
                
                async with get_db() as db:
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
                    # 注意：TransactionHistory 已在 payment_service.deduct_credits 中创建，这里不再重复
                    await db.commit()
            
            # Step 6.5: Check and unlock bottleneck lock if applicable
            bottleneck_unlocked = False
            bottleneck_unlock_result = None
            
            # Check if user is currently bottleneck-locked
            lock_status = await intimacy_service.get_bottleneck_lock_status(user_id, character_id)
            if lock_status.get("is_locked"):
                # Try to unlock with this gift's tier
                bottleneck_unlock_result = await intimacy_service.unlock_bottleneck(
                    user_id, character_id, tier
                )
                if bottleneck_unlock_result.get("unlocked"):
                    bottleneck_unlocked = True
                    logger.info(f"🔓 Bottleneck unlocked at Lv.{lock_status.get('lock_level')} with Tier {tier} gift")
            
            # Step 7: Award XP
            xp_result = await intimacy_service.award_xp(
                user_id, 
                character_id, 
                "emotional",
                force=True
            )
            actual_xp = xp_result.get("xp_awarded", 0)
            
            # Add gift-specific bonus XP (skip if bottleneck locked and XP was 0)
            bonus_xp = max(0, xp_reward - actual_xp)
            if bonus_xp > 0:
                # Check if still locked (award_xp might have returned 0 due to lock)
                if not xp_result.get("bottleneck_locked"):
                    intimacy = await intimacy_service.get_or_create_intimacy(user_id, character_id)
                    intimacy["total_xp"] += bonus_xp
                    intimacy["daily_xp_earned"] += bonus_xp
                    actual_xp += bonus_xp
            
            logger.info(f"XP awarded: {actual_xp}")
            
            # Step 8: Apply status effect (Tier 2/3 gifts)
            status_effect_applied = None
            if tier in (GiftTier.STATE_TRIGGER, GiftTier.SPEED_DATING) and "status_effect" in gift_info:
                effect_config = gift_info["status_effect"]
                
                # 检查是否有角色特定的覆盖配置
                char_overrides = effect_config.get("character_overrides", {})
                char_config = char_overrides.get(character_id, {})
                
                # 使用角色特定的 prompt_modifier，否则用默认的
                prompt_modifier = char_config.get("prompt_modifier", effect_config["prompt_modifier"])
                
                await effect_service.apply_effect(
                    user_id=user_id,
                    character_id=character_id,
                    effect_type=effect_config["type"],
                    prompt_modifier=prompt_modifier,
                    duration_messages=effect_config["duration_messages"],
                    gift_id=gift_id,
                    stage_boost=effect_config.get("stage_boost", 0),
                    allows_nsfw=char_config.get("allows_nsfw", False),
                )
                status_effect_applied = {
                    "type": effect_config["type"],
                    "duration": effect_config["duration_messages"],
                    "stage_boost": effect_config.get("stage_boost", 0),
                    "allows_nsfw": char_config.get("allows_nsfw", False),
                }
                logger.info(f"Status effect applied: {effect_config['type']} for {effect_config['duration_messages']} messages, stage_boost={effect_config.get('stage_boost', 0)}")
            
            # Step 8.5: Handle special gift effects
            cold_war_unlocked = False
            emotion_boosted = False
            
            # Apology gifts - clear cold war
            if gift_info.get("clears_cold_war"):
                try:
                    from app.services.emotion_engine_v2 import emotion_engine
                    
                    current_score = await emotion_engine.get_score(user_id, character_id)
                    was_in_cold_war = current_score <= -75
                    
                    if was_in_cold_war:
                        emotion_boost = gift_info.get("emotion_boost", 50)
                        await emotion_engine.update_score(
                            user_id, character_id,
                            delta=emotion_boost,
                            reason=f"apology_gift:{gift_type}",
                        )
                        cold_war_unlocked = True
                        logger.info(f"Cold war unlocked via apology gift: {gift_type}")
                except Exception as e:
                    logger.warning(f"Failed to process apology gift: {e}")
            
            # Emotion boost gifts
            elif gift_info.get("emotion_boost"):
                try:
                    from app.services.emotion_engine_v2 import emotion_engine
                    
                    await emotion_engine.update_score(
                        user_id, character_id,
                        delta=gift_info["emotion_boost"],
                        reason=f"gift:{gift_type}",
                    )
                    emotion_boosted = True
                except Exception as e:
                    logger.warning(f"Failed to apply emotion boost: {e}")
            
            # Force emotion (luxury gifts)
            if gift_info.get("force_emotion"):
                try:
                    from app.services.emotion_engine_v2 import emotion_engine
                    
                    # Set to maximum positive emotion
                    await emotion_engine.update_score(
                        user_id, character_id,
                        delta=100,  # Max boost
                        reason=f"luxury_gift:{gift_type}",
                    )
                except Exception as e:
                    logger.warning(f"Failed to force emotion: {e}")
            
            # Restore energy (energy drinks)
            if gift_info.get("restores_energy"):
                try:
                    from app.services.stamina_service import stamina_service
                    energy_amount = gift_info["restores_energy"]
                    await stamina_service.add_stamina(user_id, energy_amount)
                    logger.info(f"⚡ Energy restored: +{energy_amount}")
                except Exception as e:
                    logger.warning(f"Failed to restore energy: {e}")
            
            # Level boost (oath ring) - boost to near Lover stage if below
            if gift_info.get("level_boost"):
                try:
                    current_lv = xp_result.get("new_level") or xp_result.get("current_level", 1)
                    target_lv = 16  # Lover stage starts at Lv.16
                    if current_lv < target_lv:
                        # Calculate XP needed to reach target
                        from app.services.intimacy_service import IntimacyService
                        current_xp = IntimacyService.xp_for_level(current_lv)
                        target_xp = IntimacyService.xp_for_level(target_lv)
                        boost_xp = int(target_xp - current_xp)
                        if boost_xp > 0:
                            await intimacy_service.award_xp_direct(
                                user_id, character_id, boost_xp, reason="oath_ring_level_boost"
                            )
                            logger.info(f"💍 Level boost: Lv.{current_lv} → Lv.{target_lv} (+{boost_xp} XP)")
                except Exception as e:
                    logger.warning(f"Failed to apply level boost: {e}")
            
            # Global broadcast/announcement - TODO: 需要广播系统，暂时只记录日志
            if gift_info.get("global_broadcast") or gift_info.get("global_announcement"):
                logger.info(f"📢 [即将推出] 全服广播: {user_id} 送出了 {gift_type}")
            
            # Step 9: Store idempotency key
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
                "status_effect_applied": status_effect_applied,
                "bottleneck_unlocked": bottleneck_unlocked,
                "bottleneck_unlock_message": bottleneck_unlock_result.get("message") if bottleneck_unlock_result else None,
            }
            await self.store_idempotency_key(idempotency_key, user_id, gift_id, result)
            
            # =====================================================================
            # COMMIT TRANSACTION
            # =====================================================================
            
            logger.info(f"Gift transaction completed: {gift_type} from {user_id} to {character_id}")
            
            # Step 10: Trigger first_gift event (if first time sending gift)
            await self._trigger_first_gift_event(user_id, character_id)
            
            # Get current intimacy level and mood for response
            current_level = xp_result.get("new_level") or xp_result.get("current_level", 1)
            current_mood = "neutral"
            is_in_cold_war = False
            
            try:
                from app.services.emotion_engine_v2 import emotion_engine
                emotion_score = await emotion_engine.get_score(user_id, character_id)
                is_in_cold_war = emotion_score <= -75
                if emotion_score >= 50:
                    current_mood = "happy"
                elif emotion_score >= 20:
                    current_mood = "content"
                elif emotion_score >= -20:
                    current_mood = "neutral"
                elif emotion_score >= -50:
                    current_mood = "annoyed"
                else:
                    current_mood = "angry"
            except Exception as e:
                logger.warning(f"Could not get emotion state: {e}")
            
            # 判断是否是道歉礼物
            is_apology_gift = gift_info.get("clears_cold_war", False)
            
            # Generate AI response for the gift (核心：一切交互都要过AI)
            ai_response = await self.generate_ai_gift_response(
                user_id=user_id,
                character_id=character_id,
                gift=gift,
                xp_awarded=actual_xp,
                intimacy_level=current_level,
                current_mood=current_mood,
                cold_war_unlocked=cold_war_unlocked,
                is_in_cold_war=is_in_cold_war,
                is_apology_gift=is_apology_gift,
                status_effect=status_effect_applied,
            )
            
            return {
                "success": True,
                "is_duplicate": False,
                **result,
                "cold_war_unlocked": cold_war_unlocked,
                "emotion_boosted": emotion_boosted,
                "bottleneck_unlocked": bottleneck_unlocked,
                "bottleneck_unlock_message": bottleneck_unlock_result.get("message") if bottleneck_unlock_result else None,
                "ai_response": ai_response,  # AI生成的礼物反应
                "system_message": self._build_gift_system_message(
                    gift, 
                    actual_xp,
                    intimacy_level=current_level,
                    current_mood=current_mood,
                    cold_war_unlocked=cold_war_unlocked,
                    status_effect=status_effect_applied,
                ),
            }
            
        except ValueError as e:
            logger.error(f"Gift transaction failed (insufficient funds): {e}")
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Gift transaction failed: {e}", exc_info=True)
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
        current_mood: str = "neutral",
        cold_war_unlocked: bool = False,
        status_effect: Optional[dict] = None,
    ) -> str:
        """
        Build system message for AI context when user sends a gift.
        """
        gift_name = gift.get("gift_name_cn") or gift.get("gift_name")
        icon = gift.get("icon", "🎁")
        price = gift['gift_price']
        tier = gift.get("tier", GiftTier.CONSUMABLE)
        
        # Base message
        msg = (
            f"[SYSTEM] 用户送给你一份'{icon} {gift_name}'礼物（价值{price}月石）。"
            f"好感度+{xp_awarded}。当前亲密等级：{intimacy_level}。\n\n"
        )
        
        # Add status effect info if applicable
        if status_effect:
            effect_descriptions = {
                "tipsy": "你喝了这杯红酒，感觉有点微醺了。说话变得更加柔软放松，防御心降低...",
                "maid_mode": "你戴上了女仆发带，进入女仆模式。称呼用户为'主人'，语气变得恭敬服务导向...",
                "truth_mode": "你被真话药水影响了，必须诚实回答所有问题，包括隐私问题...",
            }
            effect_desc = effect_descriptions.get(
                status_effect["type"], 
                f"你受到了 {status_effect['type']} 效果的影响..."
            )
            msg += f"状态效果：{effect_desc}\n效果持续：{status_effect['duration']} 条对话\n\n"
        
        # Add cold war unlock info
        if cold_war_unlocked:
            msg += "这份道歉礼物解除了你们之间的冷战。你的心软了下来，愿意重新开始对话...\n\n"
        
        # Tone guide based on intimacy
        if intimacy_level <= 3:
            msg += "回应指南：保持礼貌但有距离感，不要太热情或亲密。"
        elif intimacy_level <= 6:
            msg += "回应指南：用朋友之间的温暖语气回应，可以稍微活泼一些。"
        elif intimacy_level <= 9:
            msg += "回应指南：可以表现得比较开心和感动，语气亲近。"
        else:
            msg += "回应指南：可以非常热情和亲密地回应，表达深厚的感情。"
        
        # Value note
        if price >= 1000:
            msg += "\n这是一份极其贵重的礼物，可以表现得非常惊喜和感动。"
        elif price >= 200:
            msg += "\n这是一份珍贵的礼物，可以表现得惊喜。"
        elif price >= 50:
            msg += "\n这是一份不错的礼物。"
        
        return msg
    
    # =========================================================================
    # AI Gift Response Generation
    # =========================================================================
    
    async def generate_ai_gift_response(
        self,
        user_id: str,
        character_id: str,
        gift: dict,
        xp_awarded: int,
        intimacy_level: int = 1,
        current_mood: str = "neutral",
        cold_war_unlocked: bool = False,
        is_in_cold_war: bool = False,
        is_apology_gift: bool = False,
        status_effect: Optional[dict] = None,
    ) -> str:
        """
        调用 LLM 生成礼物反应，而不是用静态文本。
        
        核心原则：一切交互都要过 AI，这样才有意思。
        """
        try:
            from app.services.llm_service import GrokService
            from app.api.v1.characters import get_character_by_id
            
            llm = GrokService()
            
            # 获取角色信息
            char_data = get_character_by_id(character_id)
            char_name = char_data.get("name", "AI") if char_data else "AI"
            char_prompt = char_data.get("system_prompt", "") if char_data else ""
            
            gift_name = gift.get("gift_name_cn") or gift.get("gift_name")
            icon = gift.get("icon", "🎁")
            price = gift['gift_price']
            
            # 构建礼物场景提示
            gift_context = f"""用户刚刚送给你一份礼物：{icon} {gift_name}（价值 {price} 月石）

当前状态：
- 亲密度等级：{intimacy_level}
- 当前情绪：{current_mood}
- 好感度增加：+{xp_awarded}
"""
            # 冷战状态处理
            if cold_war_unlocked:
                gift_context += "- 特殊：这是一份道歉礼物（悔过书），解除了你们之间的冷战，你的心软了\n"
            elif is_in_cold_war and not is_apology_gift:
                gift_context += "- ⚠️ 你们目前处于冷战状态！你很生气，对方送的不是道歉礼物，你可以拒绝收下或者表现得很不领情\n"
            elif is_in_cold_war and is_apology_gift:
                gift_context += "- 你们目前处于冷战状态，但对方送了道歉礼物，你的心软了一些\n"
            
            if status_effect:
                effect_desc = {
                    "tipsy": "喝了红酒有点微醺",
                    "maid_mode": "进入女仆模式",
                    "truth_mode": "被真话药水影响",
                }.get(status_effect["type"], status_effect["type"])
                gift_context += f"- 状态效果：{effect_desc}\n"
            
            # 价值感受
            if price >= 1000:
                gift_context += "\n这是一份极其贵重的礼物！"
            elif price >= 200:
                gift_context += "\n这是一份很珍贵的礼物。"
            elif price >= 50:
                gift_context += "\n这是一份不错的礼物。"
            
            system_prompt = f"""{char_prompt}

### 当前场景
{gift_context}

### 回复要求
- 用你的角色风格对收到礼物做出真实反应
- 动作和神态描写放在中文圆括号（）内
- 根据当前情绪和亲密度调整反应热情程度
- 如果是冷战后收到道歉礼物，表现出心软但还有点别扭
- 如果处于冷战但收到的不是道歉礼物，你可以拒绝、不领情、或者表现得很冷淡
- 回复简短自然，1-3句话即可，不要太长
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"[收到礼物：{icon} {gift_name}]"}
            ]
            
            response = await llm.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=200,
            )
            
            ai_response = response["choices"][0]["message"]["content"]
            logger.info(f"AI gift response generated: {ai_response[:50]}...")
            
            # 注意：消息存储已移到 gifts.py send_gift API 里统一处理
            # 这里只负责生成 AI 回复
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to generate AI gift response: {e}")
            # 降级到简单回复
            return f"（收到{gift.get('icon', '🎁')}）谢谢你的礼物～"
    
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
        """Get gift summary for AI memory context."""
        if self.mock_mode:
            gifts = [
                g for g in _MOCK_GIFTS.values()
                if g["user_id"] == user_id and g["character_id"] == character_id
            ]
            
            total_gifts = len(gifts)
            total_spent = sum(g["gift_price"] for g in gifts)
            total_xp = sum(g["xp_reward"] for g in gifts)
            
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
        
        # Database mode
        from app.core.database import get_db
        from sqlalchemy import select, func
        from app.models.database.gift_models import Gift as GiftModel
        
        async with get_db() as db:
            # 总计查询
            total_result = await db.execute(
                select(
                    func.count(GiftModel.id).label("total"),
                    func.coalesce(func.sum(GiftModel.gift_price), 0).label("spent"),
                    func.coalesce(func.sum(GiftModel.xp_reward), 0).label("xp"),
                    func.min(GiftModel.created_at).label("first_at"),
                    func.max(GiftModel.created_at).label("last_at"),
                ).where(
                    GiftModel.user_id == user_id,
                    GiftModel.character_id == character_id,
                )
            )
            row = total_result.fetchone()
            total_gifts = row.total or 0
            total_spent = row.spent or 0
            total_xp = row.xp or 0
            first_at = row.first_at
            last_at = row.last_at
            
            # Top gifts 查询
            top_result = await db.execute(
                select(
                    GiftModel.gift_type,
                    GiftModel.gift_name,
                    GiftModel.gift_name_cn,
                    func.count(GiftModel.id).label("cnt"),
                ).where(
                    GiftModel.user_id == user_id,
                    GiftModel.character_id == character_id,
                ).group_by(
                    GiftModel.gift_type,
                    GiftModel.gift_name,
                    GiftModel.gift_name_cn,
                ).order_by(func.count(GiftModel.id).desc()).limit(5)
            )
            top_rows = top_result.fetchall()
            
            # 从 catalog 获取 icon
            top_gifts = []
            for r in top_rows:
                icon = "🎁"
                cat_item = _MOCK_GIFT_CATALOG.get(r.gift_type)
                if cat_item:
                    icon = cat_item.get("icon", "🎁")
                top_gifts.append({
                    "count": r.cnt,
                    "name": r.gift_name,
                    "name_cn": r.gift_name_cn,
                    "icon": icon,
                })
        
        return {
            "total_gifts": total_gifts,
            "total_spent": total_spent,
            "total_xp_from_gifts": total_xp,
            "top_gifts": top_gifts,
            "first_gift_at": first_at,
            "last_gift_at": last_at,
        }
    
    # =========================================================================
    # Transaction History
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
    
    # =========================================================================
    # Event Triggers
    # =========================================================================
    
    async def _trigger_first_gift_event(self, user_id: str, character_id: str) -> bool:
        """
        Trigger first_gift event if not already triggered.
        This unlocks date functionality.
        """
        try:
            from app.services.game_engine import GameEngine
            
            game_engine = GameEngine()
            user_state = await game_engine._load_user_state(user_id, character_id)
            
            if "first_gift" in user_state.events:
                logger.debug(f"first_gift event already exists for {user_id}/{character_id}")
                return False
            
            # Add event
            user_state.events.append("first_gift")
            
            # Save state
            await game_engine._save_user_state(user_state)
            
            logger.info(f"first_gift event triggered for {user_id}/{character_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger first_gift event: {e}")
            return False
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def send_apology_gift(
        self,
        user_id: str,
        character_id: str,
        gift_id: str = "apology_scroll",
        session_id: Optional[str] = None,
    ) -> dict:
        """Convenience method to send apology gift and unlock cold war."""
        gift_info = await self.get_gift_info(gift_id)
        if not gift_info:
            return {"success": False, "error": "invalid_gift", "message": f"Unknown gift: {gift_id}"}
        
        if not gift_info.get("clears_cold_war"):
            return {
                "success": False, 
                "error": "not_apology_gift",
                "message": "只有道歉礼物才能解除冷战。请选择悔过书。"
            }
        
        idempotency_key = str(uuid4())
        return await self.send_gift(
            user_id=user_id,
            character_id=character_id,
            gift_type=gift_id,
            idempotency_key=idempotency_key,
            session_id=session_id,
        )


# Global service instance
gift_service = GiftService()
