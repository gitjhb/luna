"""
Stats Service
=============

Service for tracking and updating user-character relationship statistics.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database.stats_models import (
    UserCharacterStats, 
    UserCharacterEvent,
    UserCharacterMemory,
    UserCharacterGallery,
)


class StatsService:
    """Service for managing user-character statistics."""
    
    @staticmethod
    async def get_or_create_stats(
        db: AsyncSession, 
        user_id: str, 
        character_id: str
    ) -> UserCharacterStats:
        """Get existing stats or create new record."""
        result = await db.execute(
            select(UserCharacterStats).where(
                UserCharacterStats.user_id == user_id,
                UserCharacterStats.character_id == character_id
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = UserCharacterStats(
                user_id=user_id,
                character_id=character_id,
                streak_days=0,
                total_messages=0,
                total_gifts=0,
                special_events=0,
            )
            db.add(stats)
            await db.commit()
            await db.refresh(stats)
        
        return stats
    
    @staticmethod
    async def record_message(
        db: AsyncSession,
        user_id: str,
        character_id: str
    ) -> UserCharacterStats:
        """Record a message sent, update streak if needed."""
        stats = await StatsService.get_or_create_stats(db, user_id, character_id)
        
        today = date.today().isoformat()
        
        # Update message count
        stats.total_messages += 1
        
        # Check streak
        if stats.last_interaction_date:
            last_date = date.fromisoformat(stats.last_interaction_date)
            days_diff = (date.today() - last_date).days
            
            if days_diff == 1:
                # Consecutive day, increase streak
                stats.streak_days += 1
            elif days_diff > 1:
                # Streak broken, reset to 1
                stats.streak_days = 1
            # Same day, no change to streak
        else:
            # First interaction
            stats.streak_days = 1
            
            # Record first meet event (unique=True ensures only one record)
            await StatsService.record_event(
                db, user_id, character_id,
                event_type="first_meet",
                title="初次相遇",
                description="你们第一次见面",
                unique=True
            )
        
        stats.last_interaction_date = today
        await db.commit()
        await db.refresh(stats)
        
        return stats
    
    @staticmethod
    async def record_gift(
        db: AsyncSession,
        user_id: str,
        character_id: str,
        gift_type: str,
        gift_name: str = None,
        gift_icon: str = None
    ) -> UserCharacterStats:
        """Record a gift sent."""
        stats = await StatsService.get_or_create_stats(db, user_id, character_id)
        stats.total_gifts += 1
        
        # Record gift event with proper display name
        display_name = gift_name if gift_name else gift_type
        icon = gift_icon if gift_icon else "🎁"
        
        await StatsService.record_event(
            db, user_id, character_id,
            event_type="gift",
            title="收到礼物",
            description=f"你送了一份 {icon} {display_name}"
        )
        
        await db.commit()
        await db.refresh(stats)
        return stats
    
    @staticmethod
    async def record_event(
        db: AsyncSession,
        user_id: str,
        character_id: str,
        event_type: str,
        title: str,
        description: str = None,
        metadata: dict = None,
        unique: bool = False
    ) -> UserCharacterEvent:
        """Record a significant event.
        
        Args:
            unique: If True, check if event already exists and skip if duplicate.
                   Used for events like 'first_meet' that should only happen once.
        """
        import json
        
        # 检查是否需要去重（如 first_meet 只应记录一次）
        if unique or event_type == "first_meet":
            existing = await db.execute(
                select(UserCharacterEvent).where(
                    UserCharacterEvent.user_id == user_id,
                    UserCharacterEvent.character_id == character_id,
                    UserCharacterEvent.event_type == event_type
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                # 已存在，跳过记录
                return None
        
        event = UserCharacterEvent(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
            title=title,
            description=description,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.add(event)
        
        # Update special_events count
        result = await db.execute(
            select(UserCharacterStats).where(
                UserCharacterStats.user_id == user_id,
                UserCharacterStats.character_id == character_id
            )
        )
        stats = result.scalar_one_or_none()
        if stats:
            stats.special_events += 1
        
        # Note: commit handled by caller or context manager
        return event
    
    @staticmethod
    async def get_events(
        db: AsyncSession,
        user_id: str,
        character_id: str,
        limit: int = 20
    ) -> List[UserCharacterEvent]:
        """Get recent events for a character."""
        result = await db.execute(
            select(UserCharacterEvent)
            .where(
                UserCharacterEvent.user_id == user_id,
                UserCharacterEvent.character_id == character_id
            )
            .order_by(UserCharacterEvent.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def add_memory(
        db: AsyncSession,
        user_id: str,
        character_id: str,
        content: str,
        importance: str = "medium",
        source: str = None
    ) -> UserCharacterMemory:
        """Add a memory about the user."""
        memory = UserCharacterMemory(
            user_id=user_id,
            character_id=character_id,
            content=content,
            importance=importance,
            source=source,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory
    
    @staticmethod
    async def get_memories(
        db: AsyncSession,
        user_id: str,
        character_id: str,
        limit: int = 20
    ) -> List[UserCharacterMemory]:
        """Get memories for a character."""
        result = await db.execute(
            select(UserCharacterMemory)
            .where(
                UserCharacterMemory.user_id == user_id,
                UserCharacterMemory.character_id == character_id
            )
            .order_by(UserCharacterMemory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_gallery(
        db: AsyncSession,
        user_id: str,
        character_id: str
    ) -> List[UserCharacterGallery]:
        """Get gallery images for a character."""
        result = await db.execute(
            select(UserCharacterGallery)
            .where(
                UserCharacterGallery.user_id == user_id,
                UserCharacterGallery.character_id == character_id
            )
            .order_by(UserCharacterGallery.created_at.desc())
        )
        return result.scalars().all()


# Singleton instance
stats_service = StatsService()
