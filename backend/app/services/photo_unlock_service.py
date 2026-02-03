"""
Photo Unlock Service - 照片解锁系统

约会完成后根据结局解锁角色照片：
- perfect: 解锁诱惑版照片
- good/normal: 解锁普通版照片
- bad: 不解锁
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)


# 场景配置
SCENE_CONFIG = {
    "sakura": {
        "bedroom": {"name": "卧室", "required_level": 1},
        "beach": {"name": "海滩", "required_level": 20},
        "ocean": {"name": "海边露台", "required_level": 20},
        "school": {"name": "教室", "required_level": 20},
    },
    # 后续添加更多角色
}


class PhotoUnlockService:
    
    async def unlock_photo(
        self,
        user_id: str,
        character_id: str,
        scene: str,
        photo_type: str,  # 'normal' or 'perfect'
        source: str = "date",  # 解锁来源
    ) -> Dict[str, Any]:
        """
        解锁一张照片
        """
        try:
            async with get_db() as db:
                # 检查是否已解锁
                existing = await db.execute(
                    text("""
                    SELECT id FROM unlocked_photos 
                    WHERE user_id = :user_id 
                    AND character_id = :character_id 
                    AND scene = :scene 
                    AND photo_type = :photo_type
                    """),
                    {
                        "user_id": user_id,
                        "character_id": character_id,
                        "scene": scene,
                        "photo_type": photo_type,
                    }
                )
                if existing.fetchone():
                    logger.info(f"Photo already unlocked: {character_id}/{scene}/{photo_type}")
                    return {"success": True, "already_unlocked": True}
                
                # 插入解锁记录
                photo_id = str(uuid4())
                await db.execute(
                    text("""
                    INSERT INTO unlocked_photos 
                    (id, user_id, character_id, scene, photo_type, source, unlocked_at)
                    VALUES (:id, :user_id, :character_id, :scene, :photo_type, :source, :unlocked_at)
                    """),
                    {
                        "id": photo_id,
                        "user_id": user_id,
                        "character_id": character_id,
                        "scene": scene,
                        "photo_type": photo_type,
                        "source": source,
                        "unlocked_at": datetime.utcnow().isoformat(),
                    }
                )
                await db.commit()
                
                logger.info(f"📸 Photo unlocked: {character_id}/{scene}/{photo_type} for user {user_id}")
                return {
                    "success": True,
                    "photo_id": photo_id,
                    "scene": scene,
                    "photo_type": photo_type,
                }
                
        except Exception as e:
            logger.error(f"Failed to unlock photo: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_unlocked_photos(
        self,
        user_id: str,
        character_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取用户解锁的所有照片
        """
        try:
            async with get_db() as db:
                result = await db.execute(
                    text("""
                    SELECT id, scene, photo_type, source, unlocked_at
                    FROM unlocked_photos
                    WHERE user_id = :user_id AND character_id = :character_id
                    ORDER BY unlocked_at DESC
                    """),
                    {"user_id": user_id, "character_id": character_id}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "id": row[0],
                        "scene": row[1],
                        "photo_type": row[2],
                        "source": row[3],
                        "unlocked_at": row[4],
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Failed to get unlocked photos: {e}")
            return []
    
    async def is_photo_unlocked(
        self,
        user_id: str,
        character_id: str,
        scene: str,
        photo_type: str,
    ) -> bool:
        """
        检查照片是否已解锁
        """
        try:
            async with get_db() as db:
                result = await db.execute(
                    text("""
                    SELECT 1 FROM unlocked_photos 
                    WHERE user_id = :user_id 
                    AND character_id = :character_id 
                    AND scene = :scene 
                    AND photo_type = :photo_type
                    LIMIT 1
                    """),
                    {
                        "user_id": user_id,
                        "character_id": character_id,
                        "scene": scene,
                        "photo_type": photo_type,
                    }
                )
                return result.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check photo unlock: {e}")
            return False
    
    def get_unlock_photo_type(self, ending_type: str) -> Optional[str]:
        """
        根据约会结局获取应解锁的照片类型
        """
        if ending_type == "perfect":
            return "perfect"
        elif ending_type in ["good", "normal"]:
            return "normal"
        else:
            return None  # bad 结局不解锁


# Singleton
photo_unlock_service = PhotoUnlockService()
