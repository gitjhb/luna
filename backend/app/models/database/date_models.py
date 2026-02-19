"""
Date Session Database Models
持久化约会状态，避免服务器重启后丢失进行中的约会
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean
from app.models.database.billing_models import Base


class DateSessionDB(Base):
    """约会会话持久化"""
    __tablename__ = "date_sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    character_id = Column(String(50), nullable=False, index=True)
    scenario_id = Column(String(50), nullable=False)
    scenario_name = Column(String(100), nullable=False)
    
    # 状态
    current_stage = Column(Integer, default=0)
    affection_score = Column(Integer, default=0)
    status = Column(String(20), default="in_progress", index=True)  # in_progress, completed, abandoned
    is_extended = Column(Boolean, default=False)  # 是否已付费延长（30月石解锁3阶段）
    
    # 阶段数据 (JSON存储)
    stages_data = Column(JSON, default=list)
    
    # 结果
    ending_type = Column(String(50), nullable=True)
    xp_awarded = Column(Integer, default=0)
    story_summary = Column(Text, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "current_stage": self.current_stage,
            "affection_score": self.affection_score,
            "status": self.status,
            "is_extended": self.is_extended or False,
            "stages": self.stages_data or [],
            "ending_type": self.ending_type,
            "xp_awarded": self.xp_awarded,
            "story_summary": self.story_summary,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
        }


class DateCooldownDB(Base):
    """约会冷却时间持久化"""
    __tablename__ = "date_cooldowns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)
    character_id = Column(String(50), nullable=False, index=True)
    cooldown_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
