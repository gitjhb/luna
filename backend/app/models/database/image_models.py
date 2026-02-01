"""
Database Models for Image Generation History
=============================================

SQLAlchemy models for tracking image generation history.

Author: Luna AI
Date: January 2026
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import uuid
import enum

from .billing_models import Base


class ImageGenerationType(str, enum.Enum):
    """Image generation type enumeration"""
    USER_REQUEST = "user_request"      # 用户付费请求
    CHARACTER_GIFT = "character_gift"  # 角色赠送
    MILESTONE_REWARD = "milestone_reward"  # 亲密度里程碑奖励
    SPECIAL_EVENT = "special_event"    # 特殊活动


class ImageStyle(str, enum.Enum):
    """Image style enumeration"""
    SELFIE = "selfie"           # 自拍
    LIFESTYLE = "lifestyle"     # 生活照
    ARTISTIC = "artistic"       # 艺术风格
    PORTRAIT = "portrait"       # 肖像
    CASUAL = "casual"           # 日常
    ROMANTIC = "romantic"       # 浪漫
    PLAYFUL = "playful"         # 俏皮
    ELEGANT = "elegant"         # 优雅


class GeneratedImage(Base):
    """Generated image record model"""
    __tablename__ = "generated_images"
    
    image_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Generation details
    generation_type = Column(String(32), default=ImageGenerationType.USER_REQUEST.value, nullable=False)
    style = Column(String(32), default=ImageStyle.SELFIE.value, nullable=False)
    
    # Prompt information
    original_prompt = Column(Text, nullable=True)  # 用户原始请求
    final_prompt = Column(Text, nullable=False)    # 最终发送给 API 的 prompt
    negative_prompt = Column(Text, nullable=True)  # 负面提示词
    
    # Result
    image_url = Column(String(1024), nullable=False)
    thumbnail_url = Column(String(1024), nullable=True)
    aspect_ratio = Column(String(16), default="1:1", nullable=False)
    
    # Cost tracking
    cost_credits = Column(Integer, default=0, nullable=False)  # 消耗的金币数量
    is_free = Column(Boolean, default=False, nullable=False)   # 是否免费 (赠送/奖励)
    
    # Metadata
    model_used = Column(String(64), default="grok-2-image", nullable=False)
    generation_params = Column(JSON, nullable=True)  # 其他生成参数
    
    # Status
    is_nsfw = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<GeneratedImage(image_id={self.image_id}, user_id={self.user_id}, style={self.style})>"


class ImagePromptTemplate(Base):
    """Prompt template for character image generation"""
    __tablename__ = "image_prompt_templates"
    
    template_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    character_id = Column(String(128), nullable=False, index=True)
    
    # Template info
    style = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Template content
    base_prompt = Column(Text, nullable=False)  # 基础提示词模板
    style_modifiers = Column(JSON, nullable=True)  # 风格修饰词
    negative_prompt = Column(Text, nullable=True)
    
    # Settings
    aspect_ratio = Column(String(16), default="1:1", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ImagePromptTemplate(template_id={self.template_id}, style={self.style})>"
