"""
Database Models for Gift System
================================

SQLAlchemy models for gifts and idempotency keys.
Handles gift tracking, XP rewards, and deduplication.
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
    gift_price = Column(Integer, nullable=False)  # Credits spent
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
    
    # Pricing & Rewards
    price = Column(Integer, nullable=False)  # Credits
    xp_reward = Column(Integer, nullable=False)
    
    # Display
    icon = Column(String(64), nullable=True)  # Emoji or icon name
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)  # SQLite boolean
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<GiftCatalog(type={self.gift_type}, price={self.price})>"


# Gift categories
class GiftCategory:
    NORMAL = "normal"        # 普通礼物
    ROMANTIC = "romantic"    # 浪漫礼物
    APOLOGY = "apology"      # 道歉/忏悔礼物 - 用于修复关系
    LUXURY = "luxury"        # 奢华礼物
    JEWELRY = "jewelry"      # 珠宝首饰
    CLOTHING = "clothing"    # 衣服配饰
    SPICY = "spicy"          # 🔥 触发特殊剧情
    PROPS = "props"          # 互动道具


# Default gift catalog data
DEFAULT_GIFT_CATALOG = [
    # ============ 普通礼物 ============
    {
        "gift_type": "rose",
        "name": "Rose",
        "name_cn": "玫瑰花",
        "description": "A beautiful red rose",
        "description_cn": "一朵美丽的红玫瑰",
        "price": 10,
        "xp_reward": 20,
        "icon": "🌹",
        "category": GiftCategory.NORMAL,
        "sort_order": 1,
    },
    {
        "gift_type": "chocolate",
        "name": "Chocolate",
        "name_cn": "巧克力",
        "description": "Sweet chocolate box",
        "description_cn": "甜蜜的巧克力盒",
        "price": 20,
        "xp_reward": 35,
        "icon": "🍫",
        "category": GiftCategory.NORMAL,
        "sort_order": 2,
    },
    {
        "gift_type": "coffee",
        "name": "Coffee",
        "name_cn": "咖啡",
        "description": "A warm cup of coffee",
        "description_cn": "一杯温暖的咖啡",
        "price": 15,
        "xp_reward": 25,
        "icon": "☕",
        "category": GiftCategory.NORMAL,
        "sort_order": 3,
    },
    
    # ============ 浪漫礼物 ============
    {
        "gift_type": "teddy_bear",
        "name": "Teddy Bear",
        "name_cn": "泰迪熊",
        "description": "Cute and cuddly teddy bear",
        "description_cn": "可爱的泰迪熊",
        "price": 50,
        "xp_reward": 80,
        "icon": "🧸",
        "category": GiftCategory.ROMANTIC,
        "sort_order": 10,
    },
    {
        "gift_type": "premium_rose",
        "name": "Premium Rose Bouquet",
        "name_cn": "精品玫瑰花束",
        "description": "A bouquet of premium roses",
        "description_cn": "精心挑选的玫瑰花束",
        "price": 100,
        "xp_reward": 150,
        "icon": "💐",
        "category": GiftCategory.ROMANTIC,
        "sort_order": 11,
    },
    
    # ============ 道歉/忏悔礼物 ============
    {
        "gift_type": "apology_letter",
        "name": "Apology Letter",
        "name_cn": "道歉信",
        "description": "A heartfelt apology letter",
        "description_cn": "一封真诚的道歉信，表达你的歉意",
        "price": 30,
        "xp_reward": 15,
        "icon": "💌",
        "category": GiftCategory.APOLOGY,
        "sort_order": 20,
        "emotion_boost": 40,  # 解锁冷战需要提升到 -75 以上
    },
    {
        "gift_type": "apology_bouquet",
        "name": "Apology Bouquet",
        "name_cn": "道歉花束",
        "description": "A bouquet to say sorry",
        "description_cn": "表达歉意的花束，希望能获得原谅",
        "price": 80,
        "xp_reward": 30,
        "icon": "💐",
        "category": GiftCategory.APOLOGY,
        "sort_order": 21,
        "emotion_boost": 60,  # 中等道歉礼物
    },
    {
        "gift_type": "sincere_apology_box",
        "name": "Sincere Apology Gift Box",
        "name_cn": "真诚道歉礼盒",
        "description": "A premium gift box with a sincere apology",
        "description_cn": "包含真诚歉意的精美礼盒，用于修复关系",
        "price": 200,
        "xp_reward": 50,
        "icon": "🎁",
        "category": GiftCategory.APOLOGY,
        "sort_order": 22,
        "emotion_boost": 100,  # 最强道歉礼物，直接解锁冷战
    },
    {
        "gift_type": "reconciliation_cake",
        "name": "Reconciliation Cake",
        "name_cn": "和好蛋糕",
        "description": "A sweet cake to make up",
        "description_cn": "甜蜜的蛋糕，希望我们能和好",
        "price": 60,
        "xp_reward": 25,
        "icon": "🎂",
        "category": GiftCategory.APOLOGY,
        "sort_order": 23,
    },
    
    # ============ 奢华礼物 ============
    {
        "gift_type": "diamond_ring",
        "name": "Diamond Ring",
        "name_cn": "钻戒",
        "description": "A stunning diamond ring",
        "description_cn": "璀璨的钻石戒指",
        "price": 500,
        "xp_reward": 700,
        "icon": "💍",
        "category": GiftCategory.LUXURY,
        "sort_order": 30,
    },
    {
        "gift_type": "crown",
        "name": "Crown",
        "name_cn": "皇冠",
        "description": "A royal crown for your queen/king",
        "description_cn": "献给你的女王/国王的皇冠",
        "price": 1000,
        "category": GiftCategory.LUXURY,
        "xp_reward": 1500,
        "icon": "👑",
        "sort_order": 31,
    },
    
    # ============ 珠宝首饰 ============
    {
        "gift_type": "necklace",
        "name": "Pearl Necklace",
        "name_cn": "珍珠项链",
        "description": "An elegant pearl necklace",
        "description_cn": "优雅的珍珠项链",
        "price": 300,
        "xp_reward": 400,
        "icon": "📿",
        "category": GiftCategory.JEWELRY,
        "sort_order": 40,
    },
    {
        "gift_type": "earrings",
        "name": "Diamond Earrings",
        "name_cn": "钻石耳环",
        "description": "Sparkling diamond earrings",
        "description_cn": "闪耀的钻石耳环",
        "price": 400,
        "xp_reward": 500,
        "icon": "✨",
        "category": GiftCategory.JEWELRY,
        "sort_order": 41,
    },
    {
        "gift_type": "bracelet",
        "name": "Gold Bracelet",
        "name_cn": "金手链",
        "description": "A beautiful gold bracelet",
        "description_cn": "精美的金手链",
        "price": 250,
        "xp_reward": 350,
        "icon": "⭐",
        "category": GiftCategory.JEWELRY,
        "sort_order": 42,
    },
    
    # ============ 衣服配饰 ============
    {
        "gift_type": "dress",
        "name": "Evening Dress",
        "name_cn": "晚礼服",
        "description": "A stunning evening dress",
        "description_cn": "惊艳的晚礼服",
        "price": 200,
        "xp_reward": 280,
        "icon": "👗",
        "category": GiftCategory.CLOTHING,
        "sort_order": 50,
    },
    {
        "gift_type": "lingerie",
        "name": "Silk Lingerie Set",
        "name_cn": "丝绸内衣套装",
        "description": "Elegant silk lingerie",
        "description_cn": "优雅的丝绸内衣套装",
        "price": 150,
        "xp_reward": 200,
        "icon": "🎀",
        "category": GiftCategory.CLOTHING,
        "is_spicy": True,
        "requires_subscription": True,
        "sort_order": 51,
    },
    {
        "gift_type": "heels",
        "name": "High Heels",
        "name_cn": "高跟鞋",
        "description": "Elegant high heels",
        "description_cn": "优雅的高跟鞋",
        "price": 120,
        "xp_reward": 160,
        "icon": "👠",
        "category": GiftCategory.CLOTHING,
        "sort_order": 52,
    },
    
    # ============ 互动道具 ============
    {
        "gift_type": "candles",
        "name": "Scented Candles",
        "name_cn": "香薰蜡烛",
        "description": "Romantic scented candles",
        "description_cn": "浪漫的香薰蜡烛，营造氛围",
        "price": 30,
        "xp_reward": 45,
        "icon": "🕯️",
        "category": GiftCategory.PROPS,
        "sort_order": 60,
    },
    {
        "gift_type": "wine",
        "name": "Red Wine",
        "name_cn": "红酒",
        "description": "A bottle of fine red wine",
        "description_cn": "一瓶上等红酒",
        "price": 80,
        "xp_reward": 100,
        "icon": "🍷",
        "category": GiftCategory.PROPS,
        "sort_order": 61,
    },
    {
        "gift_type": "music_box",
        "name": "Music Box",
        "name_cn": "音乐盒",
        "description": "A beautiful music box",
        "description_cn": "精美的音乐盒，播放你们的歌",
        "price": 60,
        "xp_reward": 80,
        "icon": "🎵",
        "category": GiftCategory.PROPS,
        "sort_order": 62,
    },
    
    # ============ 🔥 Spicy 剧情触发 ============
    {
        "gift_type": "blindfold",
        "name": "Silk Blindfold",
        "name_cn": "丝绸眼罩",
        "description": "A soft silk blindfold for special moments",
        "description_cn": "柔软的丝绸眼罩，开启特别的时刻...",
        "price": 100,
        "xp_reward": 150,
        "icon": "🎭",
        "category": GiftCategory.SPICY,
        "is_spicy": True,
        "requires_subscription": True,
        "triggers_scene": "blindfold_scene",
        "sort_order": 70,
    },
    {
        "gift_type": "massage_oil",
        "name": "Massage Oil",
        "name_cn": "按摩精油",
        "description": "Scented massage oil for relaxation",
        "description_cn": "芳香按摩精油，让身心放松...",
        "price": 80,
        "xp_reward": 120,
        "icon": "💆",
        "category": GiftCategory.SPICY,
        "is_spicy": True,
        "requires_subscription": True,
        "triggers_scene": "massage_scene",
        "sort_order": 71,
    },
    {
        "gift_type": "champagne",
        "name": "Champagne",
        "name_cn": "香槟",
        "description": "Premium champagne for celebration",
        "description_cn": "顶级香槟，庆祝特别的夜晚...",
        "price": 150,
        "xp_reward": 200,
        "icon": "🍾",
        "category": GiftCategory.SPICY,
        "is_spicy": True,
        "requires_subscription": True,
        "triggers_scene": "champagne_night",
        "sort_order": 72,
    },
    {
        "gift_type": "private_dance",
        "name": "Private Dance Request",
        "name_cn": "私人舞蹈",
        "description": "Request a private dance performance",
        "description_cn": "请求一场私人舞蹈表演...",
        "price": 300,
        "xp_reward": 400,
        "icon": "💃",
        "category": GiftCategory.SPICY,
        "is_spicy": True,
        "requires_subscription": True,
        "triggers_scene": "private_dance",
        "sort_order": 73,
    },
]
