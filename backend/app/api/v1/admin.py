"""
Admin API - 数据库管理工具
本地开发用，不需要认证
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel
from app.services.chat_repository import chat_repo
from app.services.intimacy_service import intimacy_service
from app.services.emotion_service import emotion_service
from app.api.v1.characters import CHARACTERS

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# Schemas
# ============================================================================

class IntimacyUpdate(BaseModel):
    level: Optional[int] = None
    total_xp: Optional[int] = None


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    role: Optional[str] = None


# ============================================================================
# Users
# ============================================================================

@router.get("/users")
async def list_users(limit: int = 100, offset: int = 0):
    """列出所有用户（从 sessions 中提取 unique user_ids）"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT DISTINCT user_id, 
                   COUNT(*) as session_count,
                   MAX(updated_at) as last_active
            FROM chat_sessions 
            GROUP BY user_id
            ORDER BY last_active DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        rows = result.fetchall()
        
        return {
            "users": [
                {
                    "user_id": row[0],
                    "session_count": row[1],
                    "last_active": row[2].isoformat() if row[2] else None
                }
                for row in rows
            ],
            "total": len(rows)
        }


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    """获取用户详情"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        # 获取用户的所有 sessions
        sessions_result = await db.execute(text("""
            SELECT id, character_id, character_name, created_at, updated_at, intro_shown
            FROM chat_sessions 
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
        """), {"user_id": user_id})
        sessions = sessions_result.fetchall()
        
        # 获取亲密度数据
        intimacy_result = await db.execute(text("""
            SELECT character_id, current_level, total_xp, updated_at
            FROM user_intimacy
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        intimacy = intimacy_result.fetchall()
        
        # 获取情绪数据
        emotion_result = await db.execute(text("""
            SELECT character_id, emotion_intensity, emotional_state, updated_at
            FROM user_character_emotions
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        emotions = emotion_result.fetchall()
        
        return {
            "user_id": user_id,
            "sessions": [
                {
                    "session_id": str(s[0]),
                    "character_id": s[1],
                    "character_name": s[2],
                    "created_at": s[3].isoformat() if s[3] else None,
                    "updated_at": s[4].isoformat() if s[4] else None,
                    "intro_shown": s[5]
                }
                for s in sessions
            ],
            "intimacy": [
                {
                    "character_id": i[0],
                    "level": i[1],
                    "total_xp": i[2],
                    "updated_at": i[3].isoformat() if i[3] else None
                }
                for i in intimacy
            ],
            "emotions": [
                {
                    "character_id": e[0],
                    "score": e[1],
                    "state": e[2],
                    "updated_at": e[3].isoformat() if e[3] else None
                }
                for e in emotions
            ]
        }


# ============================================================================
# Sessions
# ============================================================================

@router.get("/sessions")
async def list_sessions(
    user_id: Optional[str] = None,
    character_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """列出所有聊天 sessions"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        if character_id:
            where_clauses.append("character_id = :character_id")
            params["character_id"] = character_id
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        result = await db.execute(text(f"""
            SELECT id, user_id, character_id, character_name, 
                   created_at, updated_at, intro_shown, total_messages
            FROM chat_sessions 
            {where_sql}
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """), params)
        rows = result.fetchall()
        
        # Get total count
        count_result = await db.execute(text(f"""
            SELECT COUNT(*) FROM chat_sessions {where_sql}
        """), params)
        total = count_result.scalar()
        
        return {
            "sessions": [
                {
                    "session_id": str(row[0]),
                    "user_id": row[1],
                    "character_id": row[2],
                    "character_name": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "intro_shown": row[6],
                    "total_messages": row[7]
                }
                for row in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """获取 session 详情"""
    session = await chat_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0
):
    """获取 session 的所有消息"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            SELECT id, role, content, tokens_used, created_at
            FROM chat_messages 
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            LIMIT :limit OFFSET :offset
        """), {"session_id": session_id, "limit": limit, "offset": offset})
        rows = result.fetchall()
        
        count_result = await db.execute(text("""
            SELECT COUNT(*) FROM chat_messages WHERE session_id = :session_id
        """), {"session_id": session_id})
        total = count_result.scalar()
        
        return {
            "messages": [
                {
                    "message_id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "tokens_used": row[3],
                    "created_at": row[4].isoformat() if row[4] else None
                }
                for row in rows
            ],
            "total": total
        }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除 session 及其所有消息"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        # Delete messages first
        await db.execute(text("""
            DELETE FROM chat_messages WHERE session_id = :session_id
        """), {"session_id": session_id})
        
        # Delete session
        result = await db.execute(text("""
            DELETE FROM chat_sessions WHERE id = :session_id
        """), {"session_id": session_id})
        
        await db.commit()
        
        return {"success": True, "deleted_session_id": session_id}


# ============================================================================
# Messages
# ============================================================================

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str):
    """删除单条消息"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            DELETE FROM chat_messages WHERE id = :message_id
        """), {"message_id": message_id})
        
        await db.commit()
        
        return {"success": True, "deleted_message_id": message_id}


@router.put("/messages/{message_id}")
async def update_message(message_id: str, data: MessageUpdate):
    """修改消息内容"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        updates = []
        params = {"message_id": message_id}
        
        if data.content is not None:
            updates.append("content = :content")
            params["content"] = data.content
        if data.role is not None:
            updates.append("role = :role")
            params["role"] = data.role
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        await db.execute(text(f"""
            UPDATE chat_messages 
            SET {', '.join(updates)}
            WHERE id = :message_id
        """), params)
        
        await db.commit()
        
        return {"success": True, "updated_message_id": message_id}


# ============================================================================
# Intimacy
# ============================================================================

@router.get("/intimacy")
async def list_all_intimacy(limit: int = 100, offset: int = 0):
    """列出所有亲密度数据"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            SELECT user_id, character_id, current_level, total_xp, updated_at
            FROM user_intimacy
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        rows = result.fetchall()
        
        return {
            "intimacy": [
                {
                    "user_id": row[0],
                    "character_id": row[1],
                    "level": row[2],
                    "total_xp": row[3],
                    "updated_at": row[4].isoformat() if row[4] else None
                }
                for row in rows
            ]
        }


@router.get("/intimacy/{user_id}/{character_id}")
async def get_intimacy(user_id: str, character_id: str):
    """获取指定用户-角色的亲密度"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            SELECT current_level, total_xp, updated_at
            FROM user_intimacy
            WHERE user_id = :user_id AND character_id = :character_id
        """), {"user_id": user_id, "character_id": character_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Intimacy record not found")
        
        return {
            "user_id": user_id,
            "character_id": character_id,
            "level": row[0],
            "total_xp": row[1],
            "updated_at": row[2].isoformat() if row[2] else None
        }


@router.put("/intimacy/{user_id}/{character_id}")
async def update_intimacy(user_id: str, character_id: str, data: IntimacyUpdate):
    """修改亲密度"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        updates = []
        params = {"user_id": user_id, "character_id": character_id}
        
        if data.level is not None:
            updates.append("current_level = :level")
            params["level"] = data.level
        if data.total_xp is not None:
            updates.append("total_xp = :total_xp")
            params["total_xp"] = data.total_xp
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = NOW()")
        
        await db.execute(text(f"""
            UPDATE user_intimacy 
            SET {', '.join(updates)}
            WHERE user_id = :user_id AND character_id = :character_id
        """), params)
        
        await db.commit()
        
        return {"success": True}


# ============================================================================
# Emotions
# ============================================================================

@router.get("/emotions")
async def list_all_emotions(limit: int = 100, offset: int = 0):
    """列出所有情绪数据"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            SELECT user_id, character_id, emotion_intensity, emotional_state, updated_at
            FROM user_character_emotions
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        rows = result.fetchall()
        
        return {
            "emotions": [
                {
                    "user_id": row[0],
                    "character_id": row[1],
                    "score": row[2],
                    "state": row[3],
                    "updated_at": row[4].isoformat() if row[4] else None
                }
                for row in rows
            ]
        }


@router.put("/emotions/{user_id}/{character_id}")
async def update_emotion(user_id: str, character_id: str, score: int, state: str = None):
    """修改情绪值"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        params = {
            "user_id": user_id, 
            "character_id": character_id,
            "score": score
        }
        
        if state:
            await db.execute(text("""
                UPDATE user_character_emotions 
                SET emotion_intensity = :score, emotional_state = :state, updated_at = NOW()
                WHERE user_id = :user_id AND character_id = :character_id
            """), {**params, "state": state})
        else:
            await db.execute(text("""
                UPDATE user_character_emotions 
                SET emotion_intensity = :score, updated_at = NOW()
                WHERE user_id = :user_id AND character_id = :character_id
            """), params)
        
        await db.commit()
        
        return {"success": True}


# ============================================================================
# Characters
# ============================================================================

@router.get("/characters")
async def list_characters(include_inactive: bool = True):
    """列出所有角色（从数据库）"""
    from app.services.character_service import character_service
    
    characters = await character_service.get_all(include_inactive=include_inactive)
    return {
        "characters": [
            {
                "character_id": c["character_id"],
                "name": c["name"],
                "description": c.get("description", ""),
                "is_active": c.get("is_active", True),
                "is_spicy": c.get("is_spicy", False),
                "sort_order": c.get("sort_order", 0),
            }
            for c in characters
        ]
    }


@router.get("/characters/{character_id}")
async def get_character_detail(character_id: str):
    """获取角色完整详情（从数据库）"""
    from app.services.character_service import character_service
    
    c = await character_service.get_by_id(character_id)
    if not c:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "character_id": c["character_id"],
        "name": c["name"],
        "description": c.get("description", ""),
        "greeting": c.get("greeting", ""),
        "system_prompt": c.get("system_prompt", ""),
        "is_active": c.get("is_active", True),
        "is_spicy": c.get("is_spicy", False),
        "sort_order": c.get("sort_order", 0),
        "personality_traits": c.get("personality_traits", []),
        "personality": c.get("personality", {}),
        "age": c.get("age"),
        "zodiac": c.get("zodiac"),
        "occupation": c.get("occupation"),
        "hobbies": c.get("hobbies", []),
        "mbti": c.get("mbti"),
        "birthday": c.get("birthday"),
        "height": c.get("height"),
        "location": c.get("location"),
    }


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    greeting: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    is_spicy: Optional[bool] = None
    sort_order: Optional[int] = None
    personality_traits: Optional[List[str]] = None
    personality: Optional[dict] = None
    age: Optional[int] = None
    zodiac: Optional[str] = None
    occupation: Optional[str] = None
    hobbies: Optional[List[str]] = None
    mbti: Optional[str] = None
    birthday: Optional[str] = None
    height: Optional[str] = None
    location: Optional[str] = None


@router.put("/characters/{character_id}")
async def update_character(character_id: str, data: CharacterUpdate):
    """更新角色"""
    from app.services.character_service import character_service
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await character_service.update(character_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {"success": True, "character": result}


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    """删除角色"""
    from app.services.character_service import character_service
    
    success = await character_service.delete(character_id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {"success": True}


# ============================================================================
# Stats
# ============================================================================

@router.get("/stats")
async def get_stats():
    """获取整体统计"""
    from app.core.database import get_db
    
    async with get_db() as db:
        from sqlalchemy import text
        
        users = await db.execute(text("SELECT COUNT(DISTINCT user_id) FROM chat_sessions"))
        sessions = await db.execute(text("SELECT COUNT(*) FROM chat_sessions"))
        messages = await db.execute(text("SELECT COUNT(*) FROM chat_messages"))
        
        return {
            "total_users": users.scalar(),
            "total_sessions": sessions.scalar(),
            "total_messages": messages.scalar()
        }
