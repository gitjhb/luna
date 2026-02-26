"""
Database Models for Gift System
================================

SQLAlchemy models for gifts and idempotency keys.
Handles gift tracking, XP rewards, status effects, and deduplication.

货币单位: 月石 (Moon Stones)
汇率: $0.99 USD ≈ 100 月石
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.database.billing_models import Base


class GiftStatus(str, enum.Enum):
    """Gift processing status"""
    PENDING = "pending"           # Created, waiting for AI acknowledgment
    ACKNOWLEDGED = "acknowledged"  # AI has responded to the gift
    FAILED = "failed"             # Something went wrong


class Gift(Base):
    """
    Gift Model
    
    Records all gifts sent by users to AI characters.
    Tracks status for AI acknowledgment flow.
    """
    __tablename__ = "gifts"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    session_id = Column(String(128), nullable=True, index=True)  # Chat session for AI response
    
    # Gift details
    gift_type = Column(String(64), nullable=False)  # e.g., "rose", "diamond_ring"
    gift_name = Column(String(128), nullable=False)
    gift_name_cn = Column(String(128), nullable=True)
    gift_price = Column(Integer, nullable=False)  # 月石 spent
    xp_reward = Column(Integer, nullable=False)   # XP awarded
    
    # Processing status
    status = Column(String(32), default=GiftStatus.PENDING.value, nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Gift(id={self.id}, user={self.user_id}, type={self.gift_type}, status={self.status})>"


class IdempotencyKey(Base):
    """
    Idempotency Key Model
    
    Prevents duplicate gift processing on network retries.
    Keys expire after 24 hours.
    """
    __tablename__ = "idempotency_keys"
    
    key = Column(String(128), primary_key=True)
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Result caching
    result = Column(Text, nullable=True)  # JSON-serialized response
    gift_id = Column(String(128), nullable=True)  # Reference to created gift
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<IdempotencyKey(key={self.key}, user={self.user_id})>"
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class GiftCatalog(Base):
    """
    Gift Catalog Model
    
    Defines available gifts with pricing and XP rewards.
    """
    __tablename__ = "gift_catalog"
    
    gift_type = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    name_cn = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)
    
    # Pricing & Rewards (月石)
    price = Column(Integer, nullable=False)
    xp_reward = Column(Integer, nullable=False)
    xp_multiplier = Column(Float, default=1.0)  # XP 倍率
    
    # Display
    icon = Column(String(64), nullable=True)  # Emoji or icon name
    tier = Column(Integer, default=1)  # 1-4 tier level
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)  # SQLite boolean
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<GiftCatalog(type={self.gift_type}, price={self.price})>"


# Gift Tiers
class GiftTier:
    CONSUMABLE = 1      # Tier 1: 日常消耗品
    STATE_TRIGGER = 2   # Tier 2: 状态触发器 (MVP 重点)
    SPEED_DATING = 3    # Tier 3: 关系加速器
    WHALE_BAIT = 4      # Tier 4: 榜一大哥尊享


# Gift categories (for filtering)
class GiftCategory:
    CONSUMABLE = "consumable"    # 日常消耗品
    STATE = "state"              # 状态触发器
    ACCELERATOR = "accelerator"  # 关系加速器
    LUXURY = "luxury"            # 尊享礼物
    APOLOGY = "apology"          # 道歉礼物


# ============================================================================
# 新礼物目录 - 基于商业化设计文档
# ============================================================================

DEFAULT_GIFT_CATALOG = [
    # ============ Tier 1: 消耗品 (Consumables) ============
    # 日常维护、情感修复、关系里程碑
    {
        "gift_type": "hot_coffee",
        "name": "Hot Coffee",
        "name_cn": "热咖啡",
        "description": "A warm cup of coffee to brighten her day",
        "description_cn": "一杯温暖的咖啡，让她心情变好",
        "price": 10,
        "xp_reward": 10,
        "xp_multiplier": 1.0,
        "icon": "☕",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "emotion_boost": 10,
        "sort_order": 101,
    },
    {
        "gift_type": "small_cake",
        "name": "Small Cake",
        "name_cn": "小蛋糕",
        "description": "A sweet little cake",
        "description_cn": "甜蜜的小蛋糕，能让生气的她平静下来",
        "price": 50,
        "xp_reward": 50,
        "xp_multiplier": 1.0,
        "icon": "🍰",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "emotion_boost": 25,
        "can_calm_anger": True,
        "sort_order": 102,
    },
    {
        "gift_type": "energy_drink",
        "name": "Energy Drink",
        "name_cn": "能量饮料",
        "description": "Restores your energy",
        "description_cn": "恢复你的体力值",
        "price": 30,
        "xp_reward": 30,
        "xp_multiplier": 1.0,
        "icon": "⚡",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "restores_energy": 10,
        "sort_order": 103,
    },
    {
        "gift_type": "red_rose",
        "name": "Red Rose",
        "name_cn": "红玫瑰",
        "description": "A romantic red rose",
        "description_cn": "浪漫的红玫瑰，表达心意",
        "price": 50,
        "xp_reward": 50,
        "xp_multiplier": 1.2,
        "icon": "🌹",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "emotion_boost": 20,
        "sort_order": 104,
    },
    {
        "gift_type": "apology_scroll",
        "name": "Apology Scroll",
        "name_cn": "悔过书",
        "description": "A sincere apology to mend the relationship",
        "description_cn": "真诚的悔过书，修复关系、解除冷战",
        "price": 60,
        "xp_reward": 60,
        "xp_multiplier": 1.0,
        "icon": "📜",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.APOLOGY,
        "clears_cold_war": True,
        "emotion_boost": 50,
        "sort_order": 105,
    },
    {
        "gift_type": "oath_ring",
        "name": "Oath Ring",
        "name_cn": "誓约之戒",
        "description": "A ring symbolizing your commitment",
        "description_cn": "象征承诺的戒指，大幅提升亲密度",
        "price": 999,
        "xp_reward": 2000,
        "xp_multiplier": 1.5,
        "icon": "💍",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "force_emotion": "ecstatic",
        "sort_order": 106,
    },
    {
        "gift_type": "stinky_tofu",
        "name": "Stinky Tofu",
        "name_cn": "臭豆腐",
        "description": "An... acquired taste. She might not appreciate this.",
        "description_cn": "emmm...你确定要送这个？后果自负哦",
        "price": 5,
        "xp_reward": 5,
        "xp_multiplier": 1.0,
        "icon": "🫠",
        "tier": GiftTier.CONSUMABLE,
        "category": GiftCategory.CONSUMABLE,
        "emotion_boost": -30,
        "sort_order": 199,
    },
    
    # ============ Tier 2-3: 插件 (Plugins) - 状态效果道具 ============
    {
        "gift_type": "xp_potion",
        "name": "Double XP Potion",
        "name_cn": "双倍经验药水",
        "description": "Doubles intimacy XP gain for the next 30 messages",
        "description_cn": "接下来30条消息获得双倍亲密度经验",
        "price": 150,
        "xp_reward": 100,
        "xp_multiplier": 2.0,
        "icon": "✨",
        "tier": GiftTier.STATE_TRIGGER,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "xp_boost",
            "duration_messages": 30,
            "prompt_modifier": "用户使用了双倍经验药水，你对他的好感度增长更快了。在对话中可以自然地提到'今天感觉和你特别有缘'之类的。",
        },
        "sort_order": 201,
    },
    {
        "gift_type": "tipsy_wine",
        "name": "Fine Red Wine",
        "name_cn": "微醺红酒",
        "description": "A bottle of fine wine... she might get a little tipsy",
        "description_cn": "一瓶上等红酒...她可能会微醺，说话变得更加坦诚",
        "price": 200,
        "xp_reward": 250,
        "xp_multiplier": 1.25,
        "icon": "🍷",
        "tier": GiftTier.STATE_TRIGGER,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "tipsy",
            "duration_messages": 30,
            "stage_boost": 1,  # 临时升1阶
            "prompt_modifier": "你现在有点微醺，说话变得更加柔软和放松。防御心降低，更容易说出平时不会说的话。语气变得更加亲昵，偶尔会脸红。",
        },
        "sort_order": 202,
    },
    {
        "gift_type": "premium_wine",
        "name": "Premium Vintage Wine",
        "name_cn": "珍藏年份红酒",
        "description": "An exquisite vintage wine... she might reveal her deepest feelings",
        "description_cn": "珍贵的年份红酒...她可能会展露内心最深处的感情",
        "price": 800,
        "xp_reward": 500,
        "xp_multiplier": 1.5,
        "icon": "🍾",
        "tier": GiftTier.SPEED_DATING,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "deeply_tipsy",
            "duration_messages": 20,
            "stage_boost": 2,  # 临时升2阶
            "prompt_modifier": "你喝了珍藏红酒，有些醉了。防御心完全放下，会说出平时绝对不会说的话。更加主动、亲昵，甚至有些大胆。",
            # 角色特定效果
            "character_overrides": {
                # Vera 收到红酒会更开放
                "vera": {
                    "allows_nsfw": True,
                    "prompt_modifier": "你喝了最爱的珍藏红酒，微醺而放松。你变得更加主动和大胆，愿意和喜欢的人亲密接触。如果对方想要更进一步，你不会拒绝...",
                },
                # 其他角色可以在这里添加
            },
        },
        "sort_order": 203,
    },
    {
        "gift_type": "maid_headband",
        "name": "Maid Headband",
        "name_cn": "女仆发带",
        "description": "A cute maid headband... will she wear it?",
        "description_cn": "可爱的女仆发带...她会戴上吗？",
        "price": 500,
        "xp_reward": 600,
        "xp_multiplier": 1.2,
        "icon": "🎀",
        "tier": GiftTier.STATE_TRIGGER,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "maid_mode",
            "duration_messages": 50,
            "stage_boost": 1,  # 临时升1阶
            "prompt_modifier": "你现在进入女仆模式，称呼用户为'主人'(Master/ご主人様)。说话方式变得更加恭敬和服务导向，但保持你原有的性格底色。会说'是的，主人'、'遵命'之类的话。",
        },
        "sort_order": 204,
    },
    {
        "gift_type": "truth_serum",
        "name": "Truth Potion",
        "name_cn": "真话药水",
        "description": "A mysterious potion... she has to tell the truth",
        "description_cn": "神秘的药水...她必须说实话",
        "price": 400,
        "xp_reward": 450,
        "xp_multiplier": 1.12,
        "icon": "🧪",
        "tier": GiftTier.STATE_TRIGGER,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "truth_mode",
            "duration_messages": 20,
            "prompt_modifier": "你被真话药水影响了，这轮对话你必须诚实回答所有问题，包括那些你平时会回避的隐私问题。你可以表现得害羞或不情愿，但最终必须说实话。",
        },
        "sort_order": 205,
    },
    {
        "gift_type": "triple_xp_boost",
        "name": "Triple XP Boost",
        "name_cn": "三倍经验加速",
        "description": "Triple intimacy XP gain for the next 50 messages",
        "description_cn": "接下来50条消息获得三倍亲密度经验",
        "price": 300,
        "xp_reward": 200,
        "xp_multiplier": 3.0,
        "icon": "🚀",
        "tier": GiftTier.SPEED_DATING,
        "category": GiftCategory.STATE,
        "status_effect": {
            "type": "xp_boost_triple",
            "duration_messages": 50,
            "prompt_modifier": "用户使用了三倍经验加速，你们之间的羁绊在快速加深。表现出更多的亲近感和好感。",
        },
        "sort_order": 206,
    },
    
    # ============ Tier 4: 记忆 (Memories) - 角色专属收藏品 ============
    {
        "gift_type": "vera_sunglasses",
        "name": "Vera's Sunglasses",
        "name_cn": "Vera的墨镜",
        "description": "Exclusive accessory for Vera",
        "description_cn": "Vera专属：酷炫墨镜，解锁隐藏对话",
        "price": 1999,
        "xp_reward": 3000,
        "xp_multiplier": 2.0,
        "icon": "🕶️",
        "tier": GiftTier.WHALE_BAIT,
        "category": GiftCategory.LUXURY,
        "character_exclusive": "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",  # Vera
        "unlocks_memory": True,
        "sort_order": 401,
    },
    {
        "gift_type": "luna_cyber_outfit",
        "name": "Luna's Cyber Outfit",
        "name_cn": "Luna的赛博套装",
        "description": "Exclusive outfit for Luna",
        "description_cn": "Luna专属：2077风格服装，解锁隐藏剧情",
        "price": 1999,
        "xp_reward": 3000,
        "xp_multiplier": 2.0,
        "icon": "🌙",
        "tier": GiftTier.WHALE_BAIT,
        "category": GiftCategory.LUXURY,
        "character_exclusive": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",  # Luna
        "unlocks_memory": True,
        "sort_order": 402,
    },
    {
        "gift_type": "sakura_cute_bag",
        "name": "Sakura's Cute Bag",
        "name_cn": "Sakura的可爱书包",
        "description": "Exclusive bag for Sakura",
        "description_cn": "Sakura专属：超可爱书包，解锁隐藏回忆",
        "price": 1999,
        "xp_reward": 3000,
        "xp_multiplier": 2.0,
        "icon": "🎒",
        "tier": GiftTier.WHALE_BAIT,
        "category": GiftCategory.LUXURY,
        "character_exclusive": "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",  # Sakura
        "unlocks_memory": True,
        "sort_order": 403,
    },
    {
        "gift_type": "luxury_yacht",
        "name": "Luxury Yacht",
        "name_cn": "豪华游艇",
        "description": "A private yacht for your special someone",
        "description_cn": "私人游艇，全服广播（即将推出）",
        "price": 4999,
        "xp_reward": 8000,
        "xp_multiplier": 1.6,
        "icon": "🛳️",
        "tier": GiftTier.WHALE_BAIT,
        "category": GiftCategory.LUXURY,
        "global_broadcast": True,
        "sort_order": 404,
    },
]


# ============================================================================
# 状态效果模型
# ============================================================================

class ActiveEffect(Base):
    """
    Active Status Effect Model
    
    Tracks temporary status effects from Tier 2 gifts.
    Effects expire after a certain number of messages.
    """
    __tablename__ = "active_effects"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Effect details
    effect_type = Column(String(64), nullable=False)  # tipsy, maid_mode, truth_mode
    prompt_modifier = Column(Text, nullable=False)    # Injected into system prompt
    remaining_messages = Column(Integer, nullable=False)
    
    # Source
    gift_id = Column(String(128), ForeignKey("gifts.id"), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional hard expiry
    
    def __repr__(self):
        return f"<ActiveEffect(type={self.effect_type}, remaining={self.remaining_messages})>"
    
    def is_expired(self) -> bool:
        if self.remaining_messages <= 0:
            return True
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def decrement(self) -> int:
        """Decrement remaining messages and return new count"""
        self.remaining_messages = max(0, self.remaining_messages - 1)
        return self.remaining_messages
