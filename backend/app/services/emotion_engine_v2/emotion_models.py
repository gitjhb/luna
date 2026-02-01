"""
Emotion Engine v2 - 数据库模型
=============================

情绪分数的持久化存储
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from datetime import datetime


def create_emotion_models(Base):
    """创建情绪相关的数据库模型"""
    
    class EmotionScore(Base):
        """
        情绪分数表 - 存储用户与角色的情绪状态
        """
        __tablename__ = "emotion_scores"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(String(64), nullable=False, index=True)
        character_id = Column(String(64), nullable=False, index=True)
        
        # 当前分数 (-100 ~ 100)
        score = Column(Integer, default=0, nullable=False)
        
        # 状态名称 (loving/happy/neutral/angry/cold_war/blocked)
        state = Column(String(32), default="neutral", nullable=False)
        
        # 统计
        highest_score = Column(Integer, default=0)  # 历史最高
        lowest_score = Column(Integer, default=0)   # 历史最低
        total_changes = Column(Integer, default=0)  # 总变化次数
        
        # 冷战/拉黑记录
        cold_war_count = Column(Integer, default=0)  # 进入冷战次数
        blocked_count = Column(Integer, default=0)   # 被拉黑次数
        
        # 时间戳
        created_at = Column(DateTime, default=func.now())
        updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
        last_interaction_at = Column(DateTime, default=func.now())
        
        # 复合索引
        __table_args__ = (
            Index('idx_emotion_user_char', 'user_id', 'character_id', unique=True),
        )
    
    class EmotionHistory(Base):
        """
        情绪变化历史 - 用于分析和调试
        """
        __tablename__ = "emotion_history"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(String(64), nullable=False, index=True)
        character_id = Column(String(64), nullable=False, index=True)
        
        # 变化详情
        score_before = Column(Integer, nullable=False)
        score_after = Column(Integer, nullable=False)
        delta = Column(Integer, nullable=False)
        
        # 触发原因
        reason = Column(String(128))  # 如: "message:insult", "gift:large", "natural_decay"
        trigger_message = Column(Text)  # 触发的消息（可选）
        
        # 分析结果
        sentiment = Column(String(16))  # positive/negative/neutral
        intent = Column(String(32))     # compliment/insult/apology/...
        intensity = Column(Float)       # 0.0 ~ 1.0
        
        # 时间戳
        created_at = Column(DateTime, default=func.now(), index=True)
        
        # 索引
        __table_args__ = (
            Index('idx_history_user_char_time', 'user_id', 'character_id', 'created_at'),
        )
    
    class CharacterPersonalityConfig(Base):
        """
        角色性格配置表
        """
        __tablename__ = "character_personality"
        
        character_id = Column(String(64), primary_key=True)
        
        # 基础性格
        name = Column(String(64), nullable=False)
        base_temperament = Column(String(32), default="cheerful")  # calm/sensitive/tsundere/cheerful
        
        # 性格参数 (0.0 ~ 1.0)
        sensitivity = Column(Float, default=0.5)      # 情绪敏感度
        forgiveness_rate = Column(Float, default=0.5) # 原谅倾向
        jealousy_level = Column(Float, default=0.3)   # 嫉妒程度
        
        # 特殊触发词 (JSON 数组)
        love_triggers = Column(Text, default="[]")    # 喜欢听的话
        hate_triggers = Column(Text, default="[]")    # 讨厌的话
        soft_spots = Column(Text, default="[]")       # 软肋话题
        
        # 情绪表现风格
        anger_style = Column(String(32), default="cold")  # cold/explosive/passive_aggressive
        happy_style = Column(String(32), default="warm")  # warm/shy/enthusiastic
        
        # 时间戳
        created_at = Column(DateTime, default=func.now())
        updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    return EmotionScore, EmotionHistory, CharacterPersonalityConfig


class EmotionDatabaseService:
    """
    情绪数据库服务
    """
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._models = None
    
    def init_models(self, Base):
        """初始化模型"""
        self._models = create_emotion_models(Base)
        return self._models
    
    @property
    def EmotionScore(self):
        return self._models[0] if self._models else None
    
    @property
    def EmotionHistory(self):
        return self._models[1] if self._models else None
    
    @property
    def CharacterPersonalityConfig(self):
        return self._models[2] if self._models else None
    
    async def get_emotion_score(self, user_id: str, character_id: str) -> dict:
        """获取情绪分数"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.EmotionScore).where(
                    self.EmotionScore.user_id == user_id,
                    self.EmotionScore.character_id == character_id,
                )
            )
            record = result.scalar_one_or_none()
            
            if record:
                return {
                    "score": record.score,
                    "state": record.state,
                    "highest_score": record.highest_score,
                    "lowest_score": record.lowest_score,
                    "cold_war_count": record.cold_war_count,
                    "blocked_count": record.blocked_count,
                    "updated_at": record.updated_at,
                }
            return None
    
    async def update_emotion_score(
        self,
        user_id: str,
        character_id: str,
        score: int,
        delta: int,
        reason: str,
        trigger_message: str = None,
        sentiment: str = None,
        intent: str = None,
        intensity: float = None,
    ):
        """更新情绪分数"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            # 获取或创建记录
            result = await session.execute(
                select(self.EmotionScore).where(
                    self.EmotionScore.user_id == user_id,
                    self.EmotionScore.character_id == character_id,
                )
            )
            record = result.scalar_one_or_none()
            
            score_before = 0
            if record:
                score_before = record.score
                record.score = score
                record.state = self._score_to_state_name(score)
                record.total_changes += 1
                record.last_interaction_at = datetime.now()
                
                # 更新最高/最低
                if score > record.highest_score:
                    record.highest_score = score
                if score < record.lowest_score:
                    record.lowest_score = score
                
                # 更新冷战/拉黑计数
                if score <= -80 and score_before > -80:
                    record.cold_war_count += 1
                if score <= -100 and score_before > -100:
                    record.blocked_count += 1
            else:
                record = self.EmotionScore(
                    user_id=user_id,
                    character_id=character_id,
                    score=score,
                    state=self._score_to_state_name(score),
                    highest_score=max(0, score),
                    lowest_score=min(0, score),
                    total_changes=1,
                    cold_war_count=1 if score <= -80 else 0,
                    blocked_count=1 if score <= -100 else 0,
                )
                session.add(record)
                score_before = 0
            
            # 记录历史
            history = self.EmotionHistory(
                user_id=user_id,
                character_id=character_id,
                score_before=score_before,
                score_after=score,
                delta=delta,
                reason=reason,
                trigger_message=trigger_message[:500] if trigger_message else None,
                sentiment=sentiment,
                intent=intent,
                intensity=intensity,
            )
            session.add(history)
            
            await session.commit()
    
    async def get_emotion_history(
        self,
        user_id: str,
        character_id: str,
        limit: int = 50,
    ) -> list:
        """获取情绪变化历史"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.EmotionHistory)
                .where(
                    self.EmotionHistory.user_id == user_id,
                    self.EmotionHistory.character_id == character_id,
                )
                .order_by(self.EmotionHistory.created_at.desc())
                .limit(limit)
            )
            records = result.scalars().all()
            
            return [
                {
                    "score_before": r.score_before,
                    "score_after": r.score_after,
                    "delta": r.delta,
                    "reason": r.reason,
                    "sentiment": r.sentiment,
                    "intent": r.intent,
                    "created_at": r.created_at,
                }
                for r in records
            ]
    
    async def get_character_personality(self, character_id: str) -> dict:
        """获取角色性格配置"""
        import json
        
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.CharacterPersonalityConfig).where(
                    self.CharacterPersonalityConfig.character_id == character_id,
                )
            )
            record = result.scalar_one_or_none()
            
            if record:
                return {
                    "name": record.name,
                    "base_temperament": record.base_temperament,
                    "sensitivity": record.sensitivity,
                    "forgiveness_rate": record.forgiveness_rate,
                    "jealousy_level": record.jealousy_level,
                    "love_triggers": json.loads(record.love_triggers or "[]"),
                    "hate_triggers": json.loads(record.hate_triggers or "[]"),
                    "soft_spots": json.loads(record.soft_spots or "[]"),
                    "anger_style": record.anger_style,
                    "happy_style": record.happy_style,
                }
            return None
    
    def _score_to_state_name(self, score: int) -> str:
        """分数转状态名"""
        if score >= 100:
            return "loving"
        elif score >= 50:
            return "happy"
        elif score >= 20:
            return "content"
        elif score >= -19:
            return "neutral"
        elif score >= -49:
            return "annoyed"
        elif score >= -79:
            return "angry"
        elif score >= -99:
            return "cold_war"
        else:
            return "blocked"
