"""
Database Models for Stamina System
==================================

体力系统数据库模型：
- UserStamina: 用户体力状态

Author: Claude
Date: February 2025
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from app.models.database.billing_models import Base


class UserStamina(Base):
    """
    用户体力表
    
    每天免费 50 条对话，体力不够时用月石购买。
    每日 0 点（UTC）重置体力。
    """
    __tablename__ = "user_stamina"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), unique=True, nullable=False, index=True)
    
    # 体力值
    current_stamina = Column(Integer, default=50, nullable=False)  # 当前体力
    max_stamina = Column(Integer, default=50, nullable=False)      # 每日最大免费体力
    
    # 重置追踪
    last_reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserStamina(user_id={self.user_id}, current={self.current_stamina}/{self.max_stamina})>"
    
    def needs_daily_reset(self) -> bool:
        """检查是否需要每日重置"""
        if not self.last_reset_at:
            return True
        
        now = datetime.utcnow()
        # 检查是否跨过了 UTC 0 点
        if now.date() > self.last_reset_at.date():
            return True
        return False
    
    def apply_daily_reset(self) -> int:
        """
        应用每日重置
        
        Returns:
            重置后的体力值
        """
        if not self.needs_daily_reset():
            return self.current_stamina
        
        self.current_stamina = self.max_stamina
        self.last_reset_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return self.current_stamina


# 体力系统常量
class StaminaConstants:
    """体力系统配置常量"""
    DAILY_FREE_STAMINA = 50         # 每日免费体力
    STAMINA_COST_PER_MESSAGE = 1    # 每条消息消耗体力
    STAMINA_PURCHASE_PRICE = 10     # 10 月石 = 10 体力
    STAMINA_PURCHASE_AMOUNT = 10    # 每次购买获得的体力
