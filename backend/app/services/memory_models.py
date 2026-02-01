"""
Memory System v2 - 数据库模型
============================

持久化存储语义记忆和情节记忆
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from datetime import datetime


def create_memory_models(Base):
    """创建记忆相关的数据库模型"""
    
    class SemanticMemoryModel(Base):
        """
        语义记忆表 - 用户特征和偏好
        """
        __tablename__ = "semantic_memories"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(String(64), nullable=False, index=True)
        character_id = Column(String(64), nullable=False, index=True)
        
        # 基本信息
        user_name = Column(String(64))
        user_nickname = Column(String(64))
        birthday = Column(String(32))
        occupation = Column(String(128))
        location = Column(String(128))
        
        # 偏好 (JSON 数组)
        likes = Column(JSON, default=[])
        dislikes = Column(JSON, default=[])
        interests = Column(JSON, default=[])
        
        # 性格特征
        personality_traits = Column(JSON, default=[])
        communication_style = Column(String(64))
        
        # 关系相关
        relationship_status = Column(String(32))
        pet_names = Column(JSON, default=[])
        important_dates = Column(JSON, default={})
        shared_jokes = Column(JSON, default=[])
        
        # 敏感话题
        sensitive_topics = Column(JSON, default=[])
        
        # 时间戳
        created_at = Column(DateTime, default=func.now())
        updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
        
        # 唯一约束
        __table_args__ = (
            Index('idx_semantic_user_char', 'user_id', 'character_id', unique=True),
        )
    
    class EpisodicMemoryModel(Base):
        """
        情节记忆表 - 重要事件和对话
        """
        __tablename__ = "episodic_memories"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        memory_id = Column(String(32), unique=True, nullable=False)
        user_id = Column(String(64), nullable=False, index=True)
        character_id = Column(String(64), nullable=False, index=True)
        
        # 事件内容
        event_type = Column(String(32), nullable=False)  # confession/fight/gift/milestone/...
        summary = Column(Text, nullable=False)           # 事件摘要
        key_dialogue = Column(JSON, default=[])          # 关键对话
        emotion_state = Column(String(32))               # 当时的情绪
        
        # 元数据
        importance = Column(Integer, default=2)          # 1-4
        strength = Column(Float, default=1.0)            # 记忆强度 0.0-1.0
        
        # 回忆统计
        recall_count = Column(Integer, default=0)
        last_recalled = Column(DateTime)
        
        # 时间戳
        created_at = Column(DateTime, default=func.now(), index=True)
        
        # 索引
        __table_args__ = (
            Index('idx_episodic_user_char', 'user_id', 'character_id'),
            Index('idx_episodic_importance', 'importance'),
        )
    
    class MemoryExtractionLog(Base):
        """
        记忆提取日志 - 调试用
        """
        __tablename__ = "memory_extraction_logs"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(String(64), nullable=False)
        character_id = Column(String(64), nullable=False)
        
        # 提取内容
        source_message = Column(Text)
        extracted_semantic = Column(JSON)
        extracted_episodic = Column(JSON)
        
        # 时间戳
        created_at = Column(DateTime, default=func.now())
    
    return SemanticMemoryModel, EpisodicMemoryModel, MemoryExtractionLog


class MemoryDatabaseService:
    """
    记忆数据库服务
    """
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._models = None
    
    def init_models(self, Base):
        """初始化模型"""
        self._models = create_memory_models(Base)
        return self._models
    
    @property
    def SemanticMemory(self):
        return self._models[0] if self._models else None
    
    @property
    def EpisodicMemory(self):
        return self._models[1] if self._models else None
    
    async def get_semantic_memory(self, user_id: str, character_id: str) -> dict:
        """获取语义记忆"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.SemanticMemory).where(
                    self.SemanticMemory.user_id == user_id,
                    self.SemanticMemory.character_id == character_id,
                )
            )
            record = result.scalar_one_or_none()
            
            if record:
                return {
                    "user_id": record.user_id,
                    "character_id": record.character_id,
                    "user_name": record.user_name,
                    "user_nickname": record.user_nickname,
                    "birthday": record.birthday,
                    "occupation": record.occupation,
                    "location": record.location,
                    "likes": record.likes or [],
                    "dislikes": record.dislikes or [],
                    "interests": record.interests or [],
                    "personality_traits": record.personality_traits or [],
                    "communication_style": record.communication_style,
                    "relationship_status": record.relationship_status,
                    "pet_names": record.pet_names or [],
                    "important_dates": record.important_dates or {},
                    "shared_jokes": record.shared_jokes or [],
                    "sensitive_topics": record.sensitive_topics or [],
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                }
            return None
    
    async def save_semantic_memory(self, user_id: str, character_id: str, data: dict):
        """保存语义记忆"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.SemanticMemory).where(
                    self.SemanticMemory.user_id == user_id,
                    self.SemanticMemory.character_id == character_id,
                )
            )
            record = result.scalar_one_or_none()
            
            if record:
                # 更新
                for key, value in data.items():
                    if key not in ["user_id", "character_id", "updated_at", "created_at"]:
                        if hasattr(record, key):
                            setattr(record, key, value)
            else:
                # 创建
                record = self.SemanticMemory(
                    user_id=user_id,
                    character_id=character_id,
                    **{k: v for k, v in data.items() if k not in ["user_id", "character_id", "updated_at", "created_at"]}
                )
                session.add(record)
            
            await session.commit()
    
    async def get_episodic_memories(
        self,
        user_id: str,
        character_id: str,
        limit: int = 100,
    ) -> list:
        """获取情节记忆列表"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(self.EpisodicMemory)
                .where(
                    self.EpisodicMemory.user_id == user_id,
                    self.EpisodicMemory.character_id == character_id,
                )
                .order_by(self.EpisodicMemory.created_at.desc())
                .limit(limit)
            )
            records = result.scalars().all()
            
            return [
                {
                    "memory_id": r.memory_id,
                    "user_id": r.user_id,
                    "character_id": r.character_id,
                    "event_type": r.event_type,
                    "summary": r.summary,
                    "key_dialogue": r.key_dialogue or [],
                    "emotion_state": r.emotion_state,
                    "importance": r.importance,
                    "strength": r.strength,
                    "recall_count": r.recall_count,
                    "last_recalled": r.last_recalled.isoformat() if r.last_recalled else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
    
    async def save_episodic_memory(self, user_id: str, character_id: str, data: dict):
        """保存情节记忆"""
        async with self.session_factory() as session:
            from sqlalchemy import select
            
            # 检查是否已存在
            result = await session.execute(
                select(self.EpisodicMemory).where(
                    self.EpisodicMemory.memory_id == data.get("memory_id"),
                )
            )
            record = result.scalar_one_or_none()
            
            if record:
                # 更新
                record.strength = data.get("strength", record.strength)
                record.recall_count = data.get("recall_count", record.recall_count)
                if data.get("last_recalled"):
                    record.last_recalled = datetime.fromisoformat(data["last_recalled"])
            else:
                # 创建
                record = self.EpisodicMemory(
                    memory_id=data.get("memory_id"),
                    user_id=user_id,
                    character_id=character_id,
                    event_type=data.get("event_type", "other"),
                    summary=data.get("summary", ""),
                    key_dialogue=data.get("key_dialogue", []),
                    emotion_state=data.get("emotion_state"),
                    importance=data.get("importance", 2),
                    strength=data.get("strength", 1.0),
                    recall_count=data.get("recall_count", 0),
                )
                session.add(record)
            
            await session.commit()
    
    async def delete_weak_memories(
        self,
        user_id: str,
        character_id: str,
        min_strength: float = 0.3,
        keep_important: bool = True,
    ):
        """删除弱记忆"""
        async with self.session_factory() as session:
            from sqlalchemy import delete, and_
            
            conditions = [
                self.EpisodicMemory.user_id == user_id,
                self.EpisodicMemory.character_id == character_id,
                self.EpisodicMemory.strength < min_strength,
            ]
            
            if keep_important:
                conditions.append(self.EpisodicMemory.importance < 3)
            
            await session.execute(
                delete(self.EpisodicMemory).where(and_(*conditions))
            )
            await session.commit()
