"""
Chat Repository - Database operations for sessions and messages
"""

import logging
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database.chat_models import ChatSession, ChatMessageDB
from app.core.database import get_db, MOCK_MODE

logger = logging.getLogger(__name__)

# ============================================================================
# In-memory fallback for when DB is not available
# ============================================================================
_memory_sessions = {}
_memory_messages = {}


class ChatRepository:
    """Repository for chat sessions and messages with DB + memory fallback"""
    
    # ========================================================================
    # Session Operations
    # ========================================================================
    
    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """Get a session by ID"""
        if MOCK_MODE:
            return _memory_sessions.get(session_id)
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                return _memory_sessions.get(session_id)
            
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            return session.to_dict() if session else None
    
    @staticmethod
    async def get_session_by_character(user_id: str, character_id: str) -> Optional[dict]:
        """Get existing session for user + character combo"""
        if MOCK_MODE:
            for s in _memory_sessions.values():
                if s.get("user_id") == user_id and str(s.get("character_id")) == str(character_id):
                    return s
            return None
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                for s in _memory_sessions.values():
                    if s.get("user_id") == user_id and str(s.get("character_id")) == str(character_id):
                        return s
                return None
            
            result = await db.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.user_id == user_id,
                        ChatSession.character_id == str(character_id)
                    )
                )
            )
            session = result.scalar_one_or_none()
            return session.to_dict() if session else None
    
    @staticmethod
    async def create_session(
        user_id: str,
        character_id: str,
        character_name: str,
        character_avatar: Optional[str] = None,
        character_background: Optional[str] = None,
    ) -> dict:
        """Create a new chat session"""
        session_id = str(uuid4())
        now = datetime.utcnow()
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "character_id": str(character_id),
            "character_name": character_name,
            "character_avatar": character_avatar,
            "character_background": character_background,
            "total_messages": 0,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        
        if MOCK_MODE:
            _memory_sessions[session_id] = session_data
            _memory_messages[session_id] = []
            return session_data
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                _memory_sessions[session_id] = session_data
                _memory_messages[session_id] = []
                return session_data
            
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                character_id=str(character_id),
                character_name=character_name,
                character_avatar=character_avatar,
                character_background=character_background,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session.to_dict()
    
    @staticmethod
    async def list_sessions(user_id: str, character_id: Optional[str] = None) -> List[dict]:
        """List all sessions for a user, optionally filtered by character"""
        
        def _add_last_message_to_sessions(sessions_list):
            """Helper to add last_message from memory messages"""
            result = []
            for s in sessions_list:
                session_dict = dict(s)  # Copy
                session_id = s.get("session_id")
                msgs = _memory_messages.get(session_id, [])
                if msgs:
                    last_msg = msgs[-1]  # Last message
                    session_dict["last_message"] = last_msg["content"][:100] if last_msg.get("content") else None
                    session_dict["last_message_at"] = last_msg["created_at"].isoformat() if last_msg.get("created_at") else None
                result.append(session_dict)
            return result
        
        if MOCK_MODE:
            sessions = [s for s in _memory_sessions.values() if s.get("user_id") == user_id]
            if character_id:
                sessions = [s for s in sessions if str(s.get("character_id")) == str(character_id)]
            return _add_last_message_to_sessions(sessions)
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                sessions = [s for s in _memory_sessions.values() if s.get("user_id") == user_id]
                if character_id:
                    sessions = [s for s in sessions if str(s.get("character_id")) == str(character_id)]
                return _add_last_message_to_sessions(sessions)
            
            query = select(ChatSession).where(ChatSession.user_id == user_id)
            if character_id:
                query = query.where(ChatSession.character_id == str(character_id))
            
            result = await db.execute(query.order_by(ChatSession.updated_at.desc()))
            sessions = result.scalars().all()
            
            # 获取每个 session 的最后一条消息
            session_dicts = []
            for s in sessions:
                session_dict = s.to_dict()
                # 查询最后一条消息
                msg_result = await db.execute(
                    select(ChatMessageDB)
                    .where(ChatMessageDB.session_id == s.id)
                    .order_by(ChatMessageDB.created_at.desc())
                    .limit(1)
                )
                last_msg = msg_result.scalar_one_or_none()
                if last_msg:
                    session_dict["last_message"] = last_msg.content[:100] if last_msg.content else None
                    session_dict["last_message_at"] = last_msg.created_at.isoformat() if last_msg.created_at else None
                session_dicts.append(session_dict)
            
            return session_dicts
    
    @staticmethod
    async def update_session(session_id: str, **kwargs) -> Optional[dict]:
        """Update session fields"""
        if MOCK_MODE:
            if session_id in _memory_sessions:
                _memory_sessions[session_id].update(kwargs)
                _memory_sessions[session_id]["updated_at"] = datetime.utcnow()
                return _memory_sessions[session_id]
            return None
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                if session_id in _memory_sessions:
                    _memory_sessions[session_id].update(kwargs)
                    _memory_sessions[session_id]["updated_at"] = datetime.utcnow()
                    return _memory_sessions[session_id]
                return None
            
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                return None
            
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            await db.commit()
            await db.refresh(session)
            return session.to_dict()
    
    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete a session and all its messages"""
        if MOCK_MODE:
            if session_id in _memory_sessions:
                del _memory_sessions[session_id]
            if session_id in _memory_messages:
                del _memory_messages[session_id]
            return True
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                if session_id in _memory_sessions:
                    del _memory_sessions[session_id]
                if session_id in _memory_messages:
                    del _memory_messages[session_id]
                return True
            
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                await db.delete(session)
                await db.commit()
            return True
    
    # ========================================================================
    # Message Operations
    # ========================================================================
    
    @staticmethod
    async def add_message(
        session_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        message_id: Optional[str] = None,
    ) -> dict:
        """Add a message to a session
        
        Args:
            message_id: Optional client-provided UUID. If not provided, generates new UUID.
                       Used for client-generated IDs to avoid message deduplication issues.
        """
        message_id = message_id or str(uuid4())
        now = datetime.utcnow()
        
        message_data = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "tokens_used": tokens_used,
            "created_at": now,
        }
        
        if MOCK_MODE:
            if session_id not in _memory_messages:
                _memory_messages[session_id] = []
            _memory_messages[session_id].append(message_data)
            return message_data
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                if session_id not in _memory_messages:
                    _memory_messages[session_id] = []
                _memory_messages[session_id].append(message_data)
                return message_data
            
            message = ChatMessageDB(
                id=message_id,
                session_id=session_id,
                role=role,
                content=content,
                tokens_used=tokens_used,
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)
            return message.to_dict()
    
    @staticmethod
    async def get_messages(
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get messages for a session"""
        if MOCK_MODE:
            msgs = _memory_messages.get(session_id, [])
            return msgs[offset : offset + limit]
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                msgs = _memory_messages.get(session_id, [])
                return msgs[offset : offset + limit]
            
            # 先获取最新的消息（倒序），然后反转为时间顺序显示
            result = await db.execute(
                select(ChatMessageDB)
                .where(ChatMessageDB.session_id == session_id)
                .order_by(ChatMessageDB.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            messages = result.scalars().all()
            # 反转为时间顺序（从早到晚）供前端显示
            return [m.to_dict() for m in reversed(messages)]
    
    @staticmethod
    async def get_all_messages(session_id: str) -> List[dict]:
        """Get ALL messages for a session (for context building)"""
        if MOCK_MODE:
            return _memory_messages.get(session_id, [])
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                return _memory_messages.get(session_id, [])
            
            result = await db.execute(
                select(ChatMessageDB)
                .where(ChatMessageDB.session_id == session_id)
                .order_by(ChatMessageDB.created_at.asc())
            )
            messages = result.scalars().all()
            return [m.to_dict() for m in messages]
    
    @staticmethod
    async def get_recent_messages(session_id: str, count: int = 2) -> List[dict]:
        """Get recent messages for duplicate checking"""
        if MOCK_MODE:
            msgs = _memory_messages.get(session_id, [])
            return msgs[-count:] if msgs else []
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                msgs = _memory_messages.get(session_id, [])
                return msgs[-count:] if msgs else []
            
            result = await db.execute(
                select(ChatMessageDB)
                .where(ChatMessageDB.session_id == session_id)
                .order_by(ChatMessageDB.created_at.desc())
                .limit(count)
            )
            messages = result.scalars().all()
            # Reverse to get chronological order
            return [m.to_dict() for m in reversed(messages)]
    
    @staticmethod
    async def count_messages(session_id: str) -> int:
        """Count messages in a session"""
        if MOCK_MODE:
            return len(_memory_messages.get(session_id, []))
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                return len(_memory_messages.get(session_id, []))
            
            from sqlalchemy import func
            result = await db.execute(
                select(func.count(ChatMessageDB.id))
                .where(ChatMessageDB.session_id == session_id)
            )
            return result.scalar() or 0
    
    @staticmethod
    async def get_messages_paginated(
        session_id: str,
        limit: int = 20,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
    ) -> List[dict]:
        """
        游标分页获取消息（类似微信）
        
        - 默认返回最新的 N 条
        - before_id: 获取该消息之前的历史消息
        - after_id: 获取该消息之后的新消息
        
        返回按时间升序排列（从早到晚）
        """
        if MOCK_MODE:
            msgs = _memory_messages.get(session_id, [])
            if before_id:
                # 找到 before_id 的位置，返回之前的消息
                idx = next((i for i, m in enumerate(msgs) if m["message_id"] == before_id), len(msgs))
                return msgs[max(0, idx - limit):idx]
            elif after_id:
                # 找到 after_id 的位置，返回之后的消息
                idx = next((i for i, m in enumerate(msgs) if m["message_id"] == after_id), -1)
                return msgs[idx + 1:idx + 1 + limit] if idx >= 0 else []
            else:
                # 返回最新的 N 条
                return msgs[-limit:] if len(msgs) > limit else msgs
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                msgs = _memory_messages.get(session_id, [])
                if before_id:
                    idx = next((i for i, m in enumerate(msgs) if m["message_id"] == before_id), len(msgs))
                    return msgs[max(0, idx - limit):idx]
                elif after_id:
                    idx = next((i for i, m in enumerate(msgs) if m["message_id"] == after_id), -1)
                    return msgs[idx + 1:idx + 1 + limit] if idx >= 0 else []
                else:
                    return msgs[-limit:] if len(msgs) > limit else msgs
            
            if before_id:
                # 获取 before_id 消息的时间戳
                ref_result = await db.execute(
                    select(ChatMessageDB.created_at)
                    .where(ChatMessageDB.id == before_id)
                )
                ref_time = ref_result.scalar_one_or_none()
                if not ref_time:
                    return []
                
                # 获取该时间之前的消息（降序取 limit 条，再反转）
                result = await db.execute(
                    select(ChatMessageDB)
                    .where(and_(
                        ChatMessageDB.session_id == session_id,
                        ChatMessageDB.created_at < ref_time
                    ))
                    .order_by(ChatMessageDB.created_at.desc())
                    .limit(limit)
                )
            elif after_id:
                # 获取 after_id 消息的时间戳
                ref_result = await db.execute(
                    select(ChatMessageDB.created_at)
                    .where(ChatMessageDB.id == after_id)
                )
                ref_time = ref_result.scalar_one_or_none()
                if not ref_time:
                    return []
                
                # 获取该时间之后的消息（升序）
                result = await db.execute(
                    select(ChatMessageDB)
                    .where(and_(
                        ChatMessageDB.session_id == session_id,
                        ChatMessageDB.created_at > ref_time
                    ))
                    .order_by(ChatMessageDB.created_at.asc())
                    .limit(limit)
                )
                messages = result.scalars().all()
                return [m.to_dict() for m in messages]
            else:
                # 默认返回最新的 N 条（降序取，再反转为升序）
                result = await db.execute(
                    select(ChatMessageDB)
                    .where(ChatMessageDB.session_id == session_id)
                    .order_by(ChatMessageDB.created_at.desc())
                    .limit(limit)
                )
            
            messages = result.scalars().all()
            # 反转为时间升序（从早到晚）
            return [m.to_dict() for m in reversed(messages)]
    
    @staticmethod
    async def has_messages_before(session_id: str, message_id: str) -> bool:
        """检查指定消息之前是否还有更多历史消息"""
        if MOCK_MODE:
            msgs = _memory_messages.get(session_id, [])
            idx = next((i for i, m in enumerate(msgs) if m["message_id"] == message_id), -1)
            return idx > 0
        
        async with get_db() as db:
            if hasattr(db, '_data'):  # MockDB
                msgs = _memory_messages.get(session_id, [])
                idx = next((i for i, m in enumerate(msgs) if m["message_id"] == message_id), -1)
                return idx > 0
            
            # 获取该消息的时间戳
            ref_result = await db.execute(
                select(ChatMessageDB.created_at)
                .where(ChatMessageDB.id == message_id)
            )
            ref_time = ref_result.scalar_one_or_none()
            if not ref_time:
                return False
            
            # 检查是否有更早的消息
            from sqlalchemy import func
            result = await db.execute(
                select(func.count(ChatMessageDB.id))
                .where(and_(
                    ChatMessageDB.session_id == session_id,
                    ChatMessageDB.created_at < ref_time
                ))
            )
            count = result.scalar() or 0
            return count > 0


# Singleton instance
chat_repo = ChatRepository()
