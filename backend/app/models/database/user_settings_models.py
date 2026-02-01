"""
User Settings Database Models
=============================

Store user preferences including NSFW mode setting.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.models.database.billing_models import Base


class UserSettings(Base):
    """User preferences and settings."""
    __tablename__ = "user_settings"
    
    user_id = Column(String(64), primary_key=True)
    
    # NSFW/Adult content setting
    nsfw_enabled = Column(Boolean, default=False)
    
    # Other settings can be added here
    language = Column(String(10), default="zh")
    notifications_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
