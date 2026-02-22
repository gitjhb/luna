"""
Story Mode Service - 故事模式
=============================

Interactive branching narrative system with LLM-generated content.
Migrated from Mio with Luna-specific enhancements.

Features:
- Multiple story types (romance, adventure, emotional, spicy)
- Dynamic scene generation with Grok
- Choice-based narrative branching
- Intimacy system integration for rewards
- Style modifiers (hotter, softer, faster)

Usage:
    from app.services.story_mode_service import story_mode_service
    
    # Start a new story
    result = await story_mode_service.start_story(user_id, character_id, story_type)
    
    # Continue with a choice
    result = await story_mode_service.continue_story(session_id, action="continue")
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from app.services.llm import grok_chat
from app.services.character_config import get_character_config

logger = logging.getLogger(__name__)

# Check for mock database mode
MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# In-memory storage for mock mode
_MOCK_STORY_SESSIONS: Dict[str, Dict] = {}


# =============================================================================
# Story Configuration
# =============================================================================

# Story types with descriptions
STORY_TYPES = {
    "romance": {
        "name": "浪漫故事",
        "name_en": "Romance",
        "icon": "💕",
        "description": "甜蜜的恋爱故事，心动的瞬间",
        "style_hint": "温柔浪漫，注重情感描写和心理活动",
    },
    "adventure": {
        "name": "冒险故事",
        "name_en": "Adventure",
        "icon": "🗺️",
        "description": "刺激的冒险旅程，一起探索未知",
        "style_hint": "紧张刺激，有悬念和转折，强调行动和对话",
    },
    "emotional": {
        "name": "情感故事",
        "name_en": "Emotional",
        "icon": "🌸",
        "description": "细腻的情感交流，深入了解彼此",
        "style_hint": "细腻深情，注重内心独白和情感变化",
    },
    "spicy": {
        "name": "情趣故事",
        "name_en": "Spicy",
        "icon": "🔥",
        "description": "大胆的亲密互动，挑战边界",
        "style_hint": "大胆直接，注重感官描写，成人向内容",
        "required_stage": "romantic",  # Need romantic stage or higher
    },
    "slice_of_life": {
        "name": "日常故事",
        "name_en": "Slice of Life",
        "icon": "☀️",
        "description": "温馨的日常点滴，平凡中的幸福",
        "style_hint": "轻松自然，生活化场景，幽默温馨",
    },
    "mystery": {
        "name": "悬疑故事",
        "name_en": "Mystery",
        "icon": "🔍",
        "description": "神秘事件，一起破解谜团",
        "style_hint": "悬念重重，线索铺设，推理解谜",
    },
}

# Style modifiers (affect narrative tone)
STYLE_MODIFIERS = {
    "normal": "保持当前节奏和风格",
    "hotter": "更激烈、更大胆、更直接的描写",
    "softer": "更温柔、更浪漫、更含蓄的描写",
    "faster": "加快节奏，推进到更关键的场景",
}

# Trigger keywords for story mode detection
STORY_TRIGGERS = [
    "写个故事", "讲个故事", "来个故事", "故事模式",
    "write a story", "tell me a story", "story mode",
    "写小说", "讲小说", "roleplay", "角色扮演",
    "/story", "小黄文", "情色故事", "18+",
]

# Story buttons for interactive navigation
STORY_BUTTONS = [
    [
        {"text": "继续 📖", "action": "continue"},
        {"text": "更激烈 🔥", "action": "hotter"},
    ],
    [
        {"text": "温柔点 💕", "action": "softer"},
        {"text": "快进 ⏩", "action": "faster"},
    ],
    [
        {"text": "结束故事 💤", "action": "end"},
    ],
]

END_BUTTONS = [
    [
        {"text": "继续 📖", "action": "continue"},
        {"text": "完美结局 ✨", "action": "end"},
    ],
    [
        {"text": "📖 新故事", "action": "new"},
    ],
]


# =============================================================================
# Story Mode Service
# =============================================================================

class StoryModeService:
    """
    Manages interactive story sessions with branching narratives.
    
    Integrates with:
    - GrokChatService for LLM generation
    - IntimacyService for XP rewards
    - CharacterConfig for persona-aware storytelling
    """
    
    def __init__(self):
        self.llm = grok_chat
        logger.info("StoryModeService initialized")
    
    # -------------------------------------------------------------------------
    # Detection
    # -------------------------------------------------------------------------
    
    def should_enter_story_mode(self, text: str) -> bool:
        """Check if user input triggers story mode."""
        lower = text.lower()
        return any(trigger in lower for trigger in STORY_TRIGGERS)
    
    def get_story_types(self, intimacy_stage: str = "strangers") -> List[Dict]:
        """
        Get available story types based on user's intimacy stage.
        
        Args:
            intimacy_stage: User's current intimacy stage with character
        
        Returns:
            List of available story type definitions
        """
        # Stage progression: strangers -> acquaintance -> friend -> close -> romantic
        stage_order = ["strangers", "acquaintance", "friend", "close", "romantic"]
        current_idx = stage_order.index(intimacy_stage) if intimacy_stage in stage_order else 0
        
        available = []
        for type_id, type_info in STORY_TYPES.items():
            required_stage = type_info.get("required_stage")
            if required_stage:
                required_idx = stage_order.index(required_stage) if required_stage in stage_order else 0
                if current_idx < required_idx:
                    # Add as locked
                    available.append({
                        "id": type_id,
                        **type_info,
                        "locked": True,
                        "unlock_hint": f"需要达到 {required_stage} 阶段",
                    })
                    continue
            
            available.append({
                "id": type_id,
                **type_info,
                "locked": False,
            })
        
        return available
    
    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get story session by ID."""
        if MOCK_MODE:
            return _MOCK_STORY_SESSIONS.get(session_id)
        
        # Database mode
        from app.core.database import get_db
        from app.models.database.story_models import StorySession
        
        try:
            async for db in get_db():
                session = db.query(StorySession).filter(
                    StorySession.id == session_id
                ).first()
                return session.to_dict() if session else None
        except Exception as e:
            logger.error(f"Error getting story session: {e}")
            return None
    
    async def get_active_session(self, user_id: str, character_id: str = None) -> Optional[Dict]:
        """Get user's active story session."""
        if MOCK_MODE:
            for session in _MOCK_STORY_SESSIONS.values():
                if session["user_id"] == user_id and session["status"] == "in_progress":
                    if character_id is None or session.get("character_id") == character_id:
                        return session
            return None
        
        # Database mode
        from app.core.database import get_db
        from app.models.database.story_models import StorySession
        
        try:
            async for db in get_db():
                query = db.query(StorySession).filter(
                    StorySession.user_id == user_id,
                    StorySession.status == "in_progress",
                )
                if character_id:
                    query = query.filter(StorySession.character_id == character_id)
                
                session = query.order_by(StorySession.last_activity.desc()).first()
                return session.to_dict() if session else None
        except Exception as e:
            logger.error(f"Error getting active session: {e}")
            return None
    
    async def _save_session(self, session: Dict) -> bool:
        """Save session to storage."""
        session_id = session["id"]
        
        if MOCK_MODE:
            _MOCK_STORY_SESSIONS[session_id] = session
            return True
        
        # Database mode
        from app.core.database import get_db
        from app.models.database.story_models import StorySession
        
        try:
            async for db in get_db():
                db_session = db.query(StorySession).filter(
                    StorySession.id == session_id
                ).first()
                
                if db_session:
                    # Update existing
                    for key, value in session.items():
                        if hasattr(db_session, key):
                            setattr(db_session, key, value)
                else:
                    # Create new
                    db_session = StorySession(**session)
                    db.add(db_session)
                
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving story session: {e}")
            return False
    
    async def _clear_session(self, session_id: str) -> bool:
        """Mark session as completed/abandoned."""
        if MOCK_MODE:
            if session_id in _MOCK_STORY_SESSIONS:
                del _MOCK_STORY_SESSIONS[session_id]
            return True
        
        # Database mode - just mark as completed, don't delete
        from app.core.database import get_db
        from app.models.database.story_models import StorySession
        
        try:
            async for db in get_db():
                db.query(StorySession).filter(
                    StorySession.id == session_id
                ).update({
                    "status": "abandoned",
                    "completed_at": datetime.utcnow(),
                })
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing story session: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # Story Generation
    # -------------------------------------------------------------------------
    
    async def start_story(
        self,
        user_id: str,
        character_id: str,
        story_type: str = "romance",
        setup_request: str = None,
    ) -> Dict[str, Any]:
        """
        Start a new story session.
        
        Args:
            user_id: User ID
            character_id: Character ID (for persona)
            story_type: Type of story (romance, adventure, etc.)
            setup_request: Optional user request for story setup
        
        Returns:
            {
                success: bool,
                session_id: str,
                intro: str,  # Story introduction
                content: str,  # First segment
                buttons: list,  # Navigation buttons
            }
        """
        logger.info(f"Starting story: user={user_id}, character={character_id}, type={story_type}")
        
        # Get character config for persona
        character_config = get_character_config(character_id)
        character_name = character_config.name if character_config else "她"
        
        # Get story type info
        type_info = STORY_TYPES.get(story_type, STORY_TYPES["romance"])
        
        # Generate story setup
        setup_prompt = self._build_setup_prompt(
            story_type=story_type,
            type_info=type_info,
            character_name=character_name,
            user_request=setup_request,
        )
        
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": setup_prompt}],
                max_tokens=400,
                temperature=0.8,
            )
            
            setup_text = response["choices"][0]["message"]["content"]
            setup = self._parse_setup_json(setup_text)
            
            if not setup:
                # Fallback setup
                setup = {
                    "title": f"{character_name}的{type_info['name']}",
                    "setting": "一个平静的下午，阳光透过窗帘洒进房间",
                    "characters": f"你和{character_name}",
                    "style": type_info["style_hint"],
                    "premise": "故事即将开始...",
                }
            
            # Create session
            session_id = str(uuid4())
            session = {
                "id": session_id,
                "user_id": user_id,
                "character_id": character_id,
                "story_type": story_type,
                "story_title": setup.get("title", ""),
                "story_setting": setup.get("setting", ""),
                "story_characters": setup.get("characters", ""),
                "story_style": "normal",
                "story_premise": setup.get("premise", ""),
                "current_segment": 0,
                "max_segments": 10,
                "segments": [],
                "choices_made": [],
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat(),
            }
            
            # Generate first segment
            first_segment = await self._generate_segment(session, "start")
            session["segments"] = [first_segment]
            
            await self._save_session(session)
            
            # Build intro text
            intro = f"📖 **{setup.get('title', '故事开始')}**\n\n"
            intro += f"_{setup.get('setting', '')}_\n"
            intro += f"_{setup.get('characters', '')}_\n\n---\n\n"
            
            return {
                "success": True,
                "session_id": session_id,
                "intro": intro,
                "content": first_segment,
                "buttons": STORY_BUTTONS,
                "segment": 1,
                "max_segments": 10,
            }
            
        except Exception as e:
            logger.error(f"Error starting story: {e}")
            return {
                "success": False,
                "error": "故事生成失败，请稍后再试",
            }
    
    async def continue_story(
        self,
        session_id: str,
        action: str = "continue",
    ) -> Dict[str, Any]:
        """
        Continue an existing story with a choice.
        
        Args:
            session_id: Story session ID
            action: User action (continue, hotter, softer, faster, end, new)
        
        Returns:
            {
                success: bool,
                content: str,  # New segment or ending
                buttons: list,
                is_ending: bool,
                rewards: dict,  # XP/intimacy rewards
            }
        """
        session = await self.get_session(session_id)
        
        if not session:
            return {
                "success": False,
                "error": "故事不存在",
                "content": "故事已经结束了，要开始新的吗？",
                "buttons": [[{"text": "📖 新故事", "action": "new"}]],
            }
        
        # Handle end action
        if action == "end":
            return await self._end_story(session)
        
        # Handle new action (clear and prompt)
        if action == "new":
            await self._clear_session(session_id)
            return {
                "success": True,
                "content": "好的，想要什么样的故事？\n\n告诉我：\n- 什么类型？（浪漫/冒险/日常）\n- 什么场景？\n- 什么风格？",
                "buttons": [],
                "expect_input": True,
            }
        
        # Update style if applicable
        if action in ["hotter", "softer", "faster"]:
            session["story_style"] = action
            session["choices_made"] = session.get("choices_made", []) + [{
                "segment": session["current_segment"],
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
            }]
        
        try:
            # Generate next segment
            segment = await self._generate_segment(session, action)
            
            session["segments"] = session.get("segments", []) + [segment]
            session["current_segment"] = len(session["segments"])
            
            await self._save_session(session)
            
            # Check if story should end
            should_end = session["current_segment"] >= session.get("max_segments", 10)
            
            return {
                "success": True,
                "content": segment,
                "buttons": END_BUTTONS if should_end else STORY_BUTTONS,
                "segment": session["current_segment"],
                "max_segments": session.get("max_segments", 10),
                "is_ending": should_end,
            }
            
        except Exception as e:
            logger.error(f"Error continuing story: {e}")
            return {
                "success": False,
                "error": "继续失败",
                "content": "呃...写不下去了，要不换个方向？",
                "buttons": STORY_BUTTONS,
            }
    
    async def _end_story(self, session: Dict) -> Dict[str, Any]:
        """End the story and calculate rewards."""
        session_id = session["id"]
        user_id = session["user_id"]
        character_id = session.get("character_id", "")
        segments_count = len(session.get("segments", []))
        
        # Calculate rewards based on engagement
        base_xp = 10
        segment_bonus = segments_count * 2
        total_xp = base_xp + segment_bonus
        
        # Award intimacy XP
        try:
            from app.services.intimacy_service import intimacy_service
            await intimacy_service.add_xp(
                user_id=user_id,
                character_id=character_id,
                amount=total_xp,
                action_type="story",
                description=f"完成故事: {session.get('story_title', '无题')}",
            )
        except Exception as e:
            logger.warning(f"Failed to award story XP: {e}")
        
        # Update session
        session["status"] = "completed"
        session["ending_type"] = "good_ending"
        session["xp_awarded"] = total_xp
        session["completed_at"] = datetime.utcnow().isoformat()
        
        await self._save_session(session)
        
        return {
            "success": True,
            "content": "\n\n---\n\n_（故事结束）_\n\n怎么样，还满意吗？😏",
            "buttons": [[{"text": "📖 再来一个", "action": "new"}]],
            "is_ending": True,
            "rewards": {
                "xp": total_xp,
                "message": f"获得 {total_xp} 亲密度！",
            },
        }
    
    async def _generate_segment(self, session: Dict, action: str) -> str:
        """Generate a story segment using LLM."""
        segments = session.get("segments", [])
        style = session.get("story_style", "normal")
        
        # Get recent context (last 3 segments)
        previous_content = "\n\n".join(segments[-3:]) if segments else "（故事刚开始）"
        
        # Build action hints
        style_hint = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS["normal"])
        
        if action == "start":
            action_hint = "这是故事的开始，要有吸引力，营造氛围，但不要太快进入主题。"
        elif action == "hotter":
            action_hint = "这一段要更激烈、更大胆。"
        elif action == "softer":
            action_hint = "这一段要更温柔、更浪漫。"
        elif action == "faster":
            action_hint = "加快节奏，推进到更关键的场景。"
        else:
            action_hint = "自然地继续故事发展。"
        
        prompt = f"""你是一位故事作家，正在写一个故事。

## 故事设定
标题: {session.get('story_title', '未命名')}
场景: {session.get('story_setting', '')}
人物: {session.get('story_characters', '')}
风格: {STORY_TYPES.get(session.get('story_type', 'romance'), {}).get('style_hint', '')}

## 之前的内容
{previous_content}

## 写作要求
{action_hint}
{style_hint}

## 规则
1. 只写200-400字的一个段落
2. 注重感官描写（视觉、听觉、触觉）
3. 有情节推进，不要原地踏步
4. 结尾留有悬念，让读者想继续
5. 所有角色都是成年人
6. 直接输出故事内容，不要元描述

继续写:"""

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.9,
        )
        
        return response["choices"][0]["message"]["content"].strip()
    
    def _build_setup_prompt(
        self,
        story_type: str,
        type_info: Dict,
        character_name: str,
        user_request: str = None,
    ) -> str:
        """Build the prompt for generating story setup."""
        base_prompt = f"""你是一个故事策划师。用户想要一个{type_info['name']}类型的故事。

角色名: {character_name}
故事类型: {type_info['name']} - {type_info['description']}
风格提示: {type_info['style_hint']}"""

        if user_request:
            base_prompt += f"\n用户的具体要求: {user_request}"
        
        base_prompt += """

请生成故事设定（JSON格式）:
{
  "title": "故事标题（吸引人的）",
  "setting": "时代背景和场景描述",
  "characters": "主要人物及关系",
  "style": "写作风格",
  "premise": "故事开端的情境"
}

只输出JSON，不要其他内容。"""

        return base_prompt
    
    def _parse_setup_json(self, text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        import json
        import re
        
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return None


# Singleton instance
story_mode_service = StoryModeService()
