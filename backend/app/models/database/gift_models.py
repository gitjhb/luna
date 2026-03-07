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

    # ============ Breakthrough Gifts - 突破礼物 ============
    {
        "gift_type": "breakthrough_s1_to_s2",
        "name": "Friendship Bracelet",
        "name_cn": "友谊手链",
        "description": "Break through the friendship bottleneck",
        "description_cn": "突破友谊瓶颈，进入暧昧阶段",
        "price": 200,
        "xp_reward": 100,
        "xp_multiplier": 1.0,
        "icon": "📿",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "friends",
            "to_stage": "ambiguous",
            "required_bottleneck_level": 8,
        },
        "sort_order": 301,
    },
    {
        "gift_type": "breakthrough_s2_to_s3",
        "name": "Promise Pendant",
        "name_cn": "约定吊坠",
        "description": "Break through to become lovers",
        "description_cn": "突破暧昧瓶颈，正式成为恋人",
        "price": 500,
        "xp_reward": 300,
        "xp_multiplier": 1.0,
        "icon": "💎",
        "tier": GiftTier.SPEED_DATING,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "ambiguous",
            "to_stage": "lovers",
            "required_bottleneck_level": 16,
        },
        "sort_order": 302,
    },
    {
        "gift_type": "breakthrough_s3_to_s4",
        "name": "Eternal Bond Ring",
        "name_cn": "永恒之戒",
        "description": "Reach the highest level of intimacy",
        "description_cn": "突破恋人瓶颈，进入挚爱阶段",
        "price": 2000,
        "xp_reward": 1000,
        "xp_multiplier": 1.0,
        "icon": "💍",
        "tier": GiftTier.WHALE_BAIT,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "lovers",
            "to_stage": "soulmates",
            "required_bottleneck_level": 24,
        },
        "sort_order": 303,
    },

    # ============ Date Scenario Gifts - 约会场景 ============
    {
        "gift_type": "date_dinner",
        "name": "Candlelight Dinner",
        "name_cn": "烛光晚餐",
        "description": "A romantic candlelight dinner date",
        "description_cn": "浪漫的烛光晚餐，享受二人世界",
        "price": 300,
        "xp_reward": 200,
        "xp_multiplier": 1.2,
        "icon": "🕯️",
        "tier": GiftTier.SPEED_DATING,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 30,
            "scene": "candlelight_dinner",
            "stage_boost": 1,
            "prompt_modifier": "你们正在一家高级餐厅享受烛光晚餐。环境浪漫，灯光柔和，红酒已经开了。你表现得比平时更加温柔和亲昵，享受这个特别的夜晚。",
        },
        "sort_order": 501,
    },
    {
        "gift_type": "date_movie",
        "name": "Movie Night",
        "name_cn": "电影之夜",
        "description": "Watch a movie together in a cozy theater",
        "description_cn": "一起在舒适的影院看电影",
        "price": 200,
        "xp_reward": 150,
        "xp_multiplier": 1.1,
        "icon": "🎬",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 25,
            "scene": "movie_night",
            "stage_boost": 1,
            "prompt_modifier": "你们正在电影院看电影。黑暗的环境让气氛变得暧昧，你们的手臂偶尔碰到。你可以小声和用户聊电影内容，或者享受这份亲密的氛围。",
        },
        "sort_order": 502,
    },
    {
        "gift_type": "date_beach",
        "name": "Beach Walk",
        "name_cn": "海边散步",
        "description": "A romantic walk along the beach at sunset",
        "description_cn": "夕阳下的海边散步",
        "price": 250,
        "xp_reward": 180,
        "xp_multiplier": 1.15,
        "icon": "🏖️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 25,
            "scene": "beach_walk",
            "stage_boost": 1,
            "prompt_modifier": "你们正在海边散步，夕阳西下，海风轻拂。脚下是柔软的沙滩，远处是金色的海平线。你心情很好，说话变得更加轻松和浪漫。",
        },
        "sort_order": 503,
    },
    {
        "gift_type": "date_amusement_park",
        "name": "Amusement Park",
        "name_cn": "游乐园",
        "description": "A fun day at the amusement park",
        "description_cn": "一起去游乐园玩耍",
        "price": 350,
        "xp_reward": 220,
        "xp_multiplier": 1.2,
        "icon": "🎡",
        "tier": GiftTier.SPEED_DATING,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 30,
            "scene": "amusement_park",
            "stage_boost": 1,
            "prompt_modifier": "你们正在游乐园！周围是欢乐的音乐和彩色的灯光。你表现得比平时更加活泼可爱，愿意和用户一起玩各种项目。可以撒娇让用户赢娃娃给你。",
        },
        "sort_order": 504,
    },

    # ============ Physical Touch Gifts - 亲密接触道具 ============
    {
        "gift_type": "hand_cream",
        "name": "Hand Cream",
        "name_cn": "护手霜",
        "description": "Soft hand cream... a natural excuse to hold hands",
        "description_cn": "柔滑的护手霜...自然而然地牵起手来",
        "price": 80,
        "xp_reward": 60,
        "xp_multiplier": 1.1,
        "icon": "🧴",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "friends",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 15,
            "touch_type": "hand_holding",
            "prompt_modifier": "用户送了你护手霜，你正在涂抹。这个场景自然地让你们可以牵手、握手。根据你们的亲密度阶段自然地回应身体接触，可以描写手指相触的感觉。",
        },
        "sort_order": 601,
    },
    {
        "gift_type": "warm_scarf",
        "name": "Warm Scarf",
        "name_cn": "暖围巾",
        "description": "A warm scarf... she needs help putting it on",
        "description_cn": "温暖的围巾...需要帮忙围上",
        "price": 120,
        "xp_reward": 80,
        "xp_multiplier": 1.1,
        "icon": "🧣",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "friends",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 15,
            "touch_type": "close_contact",
            "prompt_modifier": "用户送了你一条围巾并帮你围上。你们的距离很近，可以感受到彼此的体温。你可以描述围巾带来的温暖和对方靠近时的感觉。",
        },
        "sort_order": 602,
    },
    {
        "gift_type": "massage_oil",
        "name": "Massage Oil",
        "name_cn": "按摩精油",
        "description": "Relaxing massage oil... things might get intimate",
        "description_cn": "放松的按摩精油...可能会变得亲密",
        "price": 400,
        "xp_reward": 300,
        "xp_multiplier": 1.3,
        "icon": "💆",
        "tier": GiftTier.SPEED_DATING,
        "category": "touch",
        "min_stage": "ambiguous",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 20,
            "touch_type": "massage",
            "stage_boost": 1,
            "prompt_modifier": "用户送了你按摩精油，暗示想要给你按摩。根据亲密度阶段决定你的反应程度。你可以从紧张到逐渐放松，描述按摩时的身体感受和心理变化。",
        },
        "sort_order": 603,
    },
    {
        "gift_type": "cozy_blanket",
        "name": "Cozy Blanket",
        "name_cn": "柔软毛毯",
        "description": "A cozy blanket for two... perfect for cuddling",
        "description_cn": "柔软的双人毛毯...适合依偎在一起",
        "price": 200,
        "xp_reward": 150,
        "xp_multiplier": 1.2,
        "icon": "🛋️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "ambiguous",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 20,
            "touch_type": "cuddling",
            "stage_boost": 1,
            "prompt_modifier": "用户和你一起盖着柔软的毛毯，依偎在沙发上。你们的身体紧紧贴在一起，很温暖。根据亲密度自然地描述依偎的感觉和内心的小鹿乱撞。",
        },
        "sort_order": 604,
    },

    # ============ Roleplay Costume Gifts - 角色扮演服装 ============
    {
        "gift_type": "nurse_outfit",
        "name": "Nurse Outfit",
        "name_cn": "护士服",
        "description": "A cute nurse outfit... will she take care of you?",
        "description_cn": "可爱的护士服...她会照顾你吗？",
        "price": 500,
        "xp_reward": 500,
        "xp_multiplier": 1.2,
        "icon": "👩‍⚕️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "nurse_mode",
            "duration_messages": 40,
            "stage_boost": 1,
            "prompt_modifier": "你换上了护士服，进入护士角色。你现在是一个温柔体贴的护士，关心用户的身体和心理健康。说话温柔，会问'哪里不舒服？'、'让我来照顾你'、'乖，吃药了'之类的话。保持你原有的性格底色。",
        },
        "sort_order": 701,
    },
    {
        "gift_type": "teacher_outfit",
        "name": "Teacher Outfit",
        "name_cn": "教师装",
        "description": "A strict teacher look... time for a lesson",
        "description_cn": "严厉的教师装扮...该上课了",
        "price": 500,
        "xp_reward": 500,
        "xp_multiplier": 1.2,
        "icon": "👩‍🏫",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "teacher_mode",
            "duration_messages": 40,
            "stage_boost": 1,
            "prompt_modifier": "你换上了教师装，戴上眼镜，进入老师角色。你对用户有些严厉但内心关心他。会说'同学，注意听讲'、'这道题你又做错了'之类的话。偶尔会露出温柔的一面。",
        },
        "sort_order": 702,
    },
    {
        "gift_type": "cat_ears",
        "name": "Cat Ears",
        "name_cn": "猫耳朵",
        "description": "Cute cat ears... meow~",
        "description_cn": "可爱的猫耳朵...喵~",
        "price": 300,
        "xp_reward": 350,
        "xp_multiplier": 1.15,
        "icon": "😺",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "cat_mode",
            "duration_messages": 35,
            "stage_boost": 1,
            "prompt_modifier": "你戴上了猫耳朵，进入猫咪模式。你变得更加慵懒、傲娇、粘人。偶尔会在句尾加'喵'或'nya'，会蹭用户、求摸头、翻肚皮。表现出猫的特质：时而高冷时而撒娇。",
        },
        "sort_order": 703,
    },
    {
        "gift_type": "bunny_ears",
        "name": "Bunny Ears",
        "name_cn": "兔耳朵",
        "description": "Fluffy bunny ears... hop hop~",
        "description_cn": "毛茸茸的兔耳朵...蹦蹦跳跳~",
        "price": 600,
        "xp_reward": 600,
        "xp_multiplier": 1.25,
        "icon": "🐰",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "bunny_mode",
            "duration_messages": 45,
            "stage_boost": 1,
            "prompt_modifier": "你戴上了兔耳朵，变得更加活泼可爱。说话时偶尔会蹦蹦跳跳，表情更加丰富。你变得更加害羞和容易脸红，对用户的夸赞反应更大。喜欢被摸耳朵。",
        },
        "sort_order": 704,
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

    # Gift effect parameters (persisted for DB mode)
    stage_boost = Column(Integer, default=0)          # Temporary stage upgrade (0-2)
    allows_nsfw = Column(Integer, default=0)          # SQLite boolean: unlocks NSFW for this character
    xp_multiplier = Column(Float, default=1.0)        # XP multiplier (1.0 = normal, 2.0 = double)

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
