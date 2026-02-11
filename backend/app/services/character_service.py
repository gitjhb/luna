"""
Character Service - 角色数据服务

从数据库读取和管理角色数据
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.database.character_models import Character

logger = logging.getLogger(__name__)

# 缓存（避免每次请求都查数据库）
_characters_cache: List[Dict] = []
_cache_loaded = False


class CharacterService:
    """角色服务"""
    
    async def get_all(self, include_inactive: bool = False, lang: str = "zh") -> List[Dict]:
        """获取所有角色"""
        async with get_db() as db:
            query = select(Character).order_by(Character.sort_order, Character.name)
            if not include_inactive:
                query = query.where(Character.is_active == True)
            
            result = await db.execute(query)
            characters = result.scalars().all()
            
            return [c.to_public_dict(lang) for c in characters]
    
    async def get_by_id(self, character_id: str, lang: str = "zh") -> Optional[Dict]:
        """根据 ID 获取角色"""
        async with get_db() as db:
            result = await db.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()
            
            if character:
                return character.to_dict(lang)
            return None
    
    async def get_public_by_id(self, character_id: str, lang: str = "zh") -> Optional[Dict]:
        """根据 ID 获取角色（公开信息，不含 system_prompt）"""
        async with get_db() as db:
            result = await db.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()
            
            if character:
                return character.to_public_dict(lang)
            return None
    
    async def create(self, data: Dict[str, Any]) -> Dict:
        """创建角色"""
        async with get_db() as db:
            character = Character(**data)
            db.add(character)
            await db.commit()
            await db.refresh(character)
            
            logger.info(f"Created character: {character.name} ({character.id})")
            return character.to_dict()
    
    async def update(self, character_id: str, data: Dict[str, Any]) -> Optional[Dict]:
        """更新角色"""
        async with get_db() as db:
            result = await db.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()
            
            if not character:
                return None
            
            # 更新字段
            for key, value in data.items():
                if hasattr(character, key) and value is not None:
                    setattr(character, key, value)
            
            await db.commit()
            await db.refresh(character)
            
            logger.info(f"Updated character: {character.name} ({character.id})")
            return character.to_dict()
    
    async def delete(self, character_id: str) -> bool:
        """删除角色"""
        async with get_db() as db:
            result = await db.execute(
                delete(Character).where(Character.id == character_id)
            )
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Deleted character: {character_id}")
                return True
            return False
    
    async def get_greeting(self, character_id: str, lang: str = "zh") -> Optional[str]:
        """获取角色的 greeting"""
        character = await self.get_by_id(character_id, lang)
        if character:
            return character.get("greeting")
        return None
    
    async def get_system_prompt(self, character_id: str, lang: str = "zh") -> Optional[str]:
        """获取角色的 system_prompt"""
        character = await self.get_by_id(character_id, lang)
        if character:
            return character.get("system_prompt")
        return None


# 单例
character_service = CharacterService()


# 兼容旧代码的函数
async def get_character_by_id(character_id: str) -> Optional[Dict]:
    """兼容旧代码"""
    return await character_service.get_by_id(character_id)


async def get_all_characters(include_inactive: bool = False) -> List[Dict]:
    """兼容旧代码"""
    return await character_service.get_all(include_inactive)
