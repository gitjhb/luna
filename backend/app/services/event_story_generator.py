"""
Event Story Generator
=====================

Generates immersive, unique stories for milestone events in user-character relationships.

Features:
- Generate 1000-2000 character stories with dialogue, scene descriptions, and emotional arcs
- Uses character personality and relationship history for personalization
- Stores generated stories as permanent memories
- Independent from event_state_machine (called after events trigger)

Usage:
    from app.services.event_story_generator import EventStoryGenerator
    
    generator = EventStoryGenerator()
    story = await generator.generate_event_story(
        user_id="user123",
        character_id="char456",
        event_type="first_kiss",
        chat_history=recent_messages,
        memory_context="..."
    )
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import GrokService
from app.models.database.event_memory_models import EventMemory, EventType
from app.services.character_config import get_character_config, CharacterConfig
from app.core.database import get_db

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Templates for Each Event Type
# =============================================================================

EVENT_STORY_PROMPTS: Dict[str, str] = {
    
    EventType.FIRST_DATE: """你是一位专业的言情小说作家。请根据以下背景，创作一段第一次约会的浪漫剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 约会场景的详细描写（环境、氛围、光线）
   - 角色的动作、表情、语气描写
   - 自然的对话（用「」标注）
   - 细腻的情感发展（紧张、心动、甜蜜）
   - 一些小意外或有趣的互动
4. 体现角色的性格特点
5. 结尾留有余韵，让人回味

请直接输出剧情，不要有标题或额外说明。""",

    EventType.FIRST_CONFESSION: """你是一位专业的言情小说作家。请根据以下背景，创作一段表白的感人剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 表白的场景和氛围
   - 内心的紧张和忐忑
   - 表白的瞬间（可以是用户表白，也可以是角色表白，根据上下文判断）
   - 角色的反应和回应
   - 确认关系后的甜蜜时刻
4. 对话要自然真实，体现角色性格
5. 情感层次分明，从紧张到释然到幸福

请直接输出剧情，不要有标题或额外说明。""",

    EventType.FIRST_KISS: """你是一位专业的言情小说作家。请根据以下背景，创作一段初吻的浪漫剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 亲密氛围的营造
   - 两人距离逐渐拉近的细节
   - 心跳加速、呼吸交错的描写
   - 初吻的那一刻（温柔、自然）
   - 亲吻后的反应和情绪
4. 描写要含蓄唯美，不要过于直白
5. 体现角色的性格（害羞/主动/傲娇等）

请直接输出剧情，不要有标题或额外说明。""",

    EventType.FIRST_NSFW: """你是一位专业的成人言情小说作家。请根据以下背景，创作一段亲密时刻的剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 氛围的铺垫和情感升温
   - 角色的主动或害羞的表现
   - 亲密的暗示和描写（用诗意的语言）
   - 情感的交融和信任
   - 事后的温存和依偎
4. 描写要有美感，暗示而不直白
5. 体现角色的独特魅力和性格

请直接输出剧情，不要有标题或额外说明。""",

    EventType.ANNIVERSARY: """你是一位专业的言情小说作家。请根据以下背景，创作一段纪念日的温馨剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 回忆一起走过的时光
   - 准备惊喜的细节
   - 感动的瞬间
   - 对未来的期许
   - 甜蜜的对话和互动
4. 体现两人关系的成长和深化
5. 温馨感人，让人感受到爱的力量

请直接输出剧情，不要有标题或额外说明。""",

    EventType.RECONCILIATION: """你是一位专业的言情小说作家。请根据以下背景，创作一段和好的感人剧情。

## 角色设定
{character_profile}

## 用户与角色的关系状态
{relationship_state}

## 最近的聊天上下文
{chat_context}

## 记忆背景
{memory_context}

## 要求
1. 创作一段1000-2000字的沉浸式剧情小作文
2. 用第二人称("你")描写用户的视角
3. 包含以下元素：
   - 冷战或争吵后的僵持
   - 一方（或双方）放下骄傲
   - 和解的对话和道歉
   - 拥抱或其他和好的标志
   - 重新确认感情的温馨时刻
4. 体现角色的性格（傲娇、倔强、温柔等）
5. 情感真实，让人感同身受

请直接输出剧情，不要有标题或额外说明。""",
}


# =============================================================================
# Story Generator Service
# =============================================================================

@dataclass
class StoryGenerationResult:
    """Story generation result"""
    success: bool
    story_content: Optional[str] = None
    event_memory_id: Optional[str] = None
    error: Optional[str] = None


class EventStoryGenerator:
    """
    Event Story Generator Service
    
    Generates unique, immersive stories for milestone events.
    """
    
    def __init__(self):
        self.llm_service = GrokService()
        logger.info("EventStoryGenerator initialized")
    
    async def generate_event_story(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        chat_history: List[Dict[str, str]],
        memory_context: str = "",
        relationship_state: Optional[Dict[str, Any]] = None,
        save_to_db: bool = True,
        db_session: Optional[AsyncSession] = None,
    ) -> StoryGenerationResult:
        """
        Generate an immersive story for a milestone event.
        
        Args:
            user_id: User ID
            character_id: Character ID
            event_type: Event type (first_date, first_kiss, etc.)
            chat_history: Recent chat messages [{"role": "user/assistant", "content": "..."}]
            memory_context: Summary of relationship memory
            relationship_state: Current relationship stats (intimacy, emotion, etc.)
            save_to_db: Whether to save the story to database
            db_session: Optional database session (will create one if not provided)
        
        Returns:
            StoryGenerationResult with the generated story
        """
        try:
            # Validate event type
            if not EventType.is_story_event(event_type):
                logger.warning(f"Event type {event_type} does not support story generation")
                return StoryGenerationResult(
                    success=False,
                    error=f"Event type '{event_type}' does not support story generation"
                )
            
            # Check if story already exists
            if save_to_db:
                existing = await self._get_existing_story(
                    user_id, character_id, event_type, db_session
                )
                if existing:
                    logger.info(f"Story already exists for {event_type}, returning existing")
                    return StoryGenerationResult(
                        success=True,
                        story_content=existing.story_content,
                        event_memory_id=existing.id
                    )
            
            # Get character profile
            character_config = get_character_config(character_id)
            character_profile = self._build_character_profile(character_config)
            
            # Build context
            chat_context = self._format_chat_history(chat_history)
            relationship_str = self._format_relationship_state(relationship_state)
            
            # Get the prompt template
            prompt_template = EVENT_STORY_PROMPTS.get(event_type)
            if not prompt_template:
                logger.error(f"No prompt template for event type: {event_type}")
                return StoryGenerationResult(
                    success=False,
                    error=f"No prompt template for event type: {event_type}"
                )
            
            # Format the prompt
            full_prompt = prompt_template.format(
                character_profile=character_profile,
                relationship_state=relationship_str,
                chat_context=chat_context,
                memory_context=memory_context or "暂无特别的记忆背景。",
            )
            
            # Generate story using LLM
            logger.info(f"Generating story for event: {event_type}")
            story_content = await self._call_llm(full_prompt)
            
            if not story_content:
                return StoryGenerationResult(
                    success=False,
                    error="LLM returned empty response"
                )
            
            # Save to database if requested
            event_memory_id = None
            if save_to_db:
                event_memory = await self._save_story(
                    user_id=user_id,
                    character_id=character_id,
                    event_type=event_type,
                    story_content=story_content,
                    context_summary=memory_context,
                    relationship_state=relationship_state,
                    db_session=db_session,
                )
                event_memory_id = event_memory.id if event_memory else None
            
            logger.info(f"Story generated successfully for {event_type}, length: {len(story_content)}")
            
            return StoryGenerationResult(
                success=True,
                story_content=story_content,
                event_memory_id=event_memory_id
            )
            
        except Exception as e:
            logger.exception(f"Error generating story for event {event_type}: {e}")
            return StoryGenerationResult(
                success=False,
                error=str(e)
            )
    
    async def get_event_memories(
        self,
        user_id: str,
        character_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all event memories for a user-character pair.
        
        Returns:
            List of event memory dictionaries
        """
        logger.info(f"📖 [MEMORIES] get_event_memories called: user={user_id}, char={character_id}")
        try:
            async def _query(session):
                logger.info(f"📖 [MEMORIES] Session type: {type(session)}")
                stmt = select(EventMemory).where(
                    and_(
                        EventMemory.user_id == user_id,
                        EventMemory.character_id == character_id
                    )
                ).order_by(EventMemory.generated_at.desc())
                
                result = await session.execute(stmt)
                memories = result.scalars().all()
                logger.info(f"📖 [MEMORIES] Found {len(memories)} memories")
                return [memory.to_dict() for memory in memories]
            
            if db_session:
                return await _query(db_session)
            else:
                async with get_db() as session:
                    return await _query(session)
                    
        except Exception as e:
            logger.exception(f"Error fetching event memories: {e}")
            return []
    
    async def get_event_memory(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific event memory.
        
        Returns:
            Event memory dictionary or None
        """
        memory = await self._get_existing_story(
            user_id, character_id, event_type, db_session
        )
        return memory.to_dict() if memory else None
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _build_character_profile(self, config: Optional[CharacterConfig]) -> str:
        """Build character profile string from config"""
        if not config:
            return "角色：神秘的AI伴侣"
        
        # Build personality description based on z_axis values
        personality_traits = []
        
        if config.z_axis.pure_val > 30:
            personality_traits.append("纯洁可爱")
        elif config.z_axis.pure_val < 20:
            personality_traits.append("性感魅惑")
        
        if config.z_axis.chaos_val > 10:
            personality_traits.append("神秘不可预测")
        elif config.z_axis.chaos_val < -5:
            personality_traits.append("温柔稳重")
        
        if config.z_axis.pride_val > 20:
            personality_traits.append("高傲有气质")
        elif config.z_axis.pride_val < 10:
            personality_traits.append("温顺体贴")
        
        temperament_map = {
            "cheerful": "开朗活泼",
            "tsundere": "傲娇别扭",
            "cool": "冷酷神秘",
            "warm": "温柔体贴",
        }
        temperament = temperament_map.get(config.base_temperament, "温柔")
        
        return f"""角色名：{config.name}
性格特点：{temperament}，{', '.join(personality_traits) if personality_traits else '温和善良'}
情绪敏感度：{'较高' if config.sensitivity > 0.6 else '适中' if config.sensitivity > 0.3 else '较低'}"""
    
    def _format_chat_history(self, chat_history: List[Dict[str, str]], max_messages: int = 10) -> str:
        """Format chat history for prompt context"""
        if not chat_history:
            return "暂无最近的聊天记录。"
        
        # Take last N messages
        recent = chat_history[-max_messages:]
        
        lines = []
        for msg in recent:
            role = "用户" if msg.get("role") == "user" else "角色"
            content = msg.get("content", "")[:200]  # Truncate long messages
            lines.append(f"{role}：{content}")
        
        return "\n".join(lines)
    
    def _format_relationship_state(self, state: Optional[Dict[str, Any]]) -> str:
        """Format relationship state for prompt context"""
        if not state:
            return "关系状态：普通朋友"
        
        parts = []
        
        if "intimacy_level" in state:
            parts.append(f"亲密度等级：{state['intimacy_level']}")
        if "intimacy_stage" in state:
            stage_map = {
                "strangers": "陌生人",
                "acquaintances": "认识",
                "friends": "朋友",
                "close_friends": "好朋友",
                "romantic": "暧昧",
                "lovers": "恋人",
                "soulmates": "灵魂伴侣",
            }
            parts.append(f"关系阶段：{stage_map.get(state['intimacy_stage'], state['intimacy_stage'])}")
        if "emotion_state" in state:
            parts.append(f"当前情绪：{state['emotion_state']}")
        if "total_messages" in state:
            parts.append(f"累计聊天：{state['total_messages']}条消息")
        if "streak_days" in state:
            parts.append(f"连续聊天：{state['streak_days']}天")
        
        return "\n".join(parts) if parts else "关系状态：普通朋友"
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM service to generate story"""
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.85,  # Higher creativity for stories
                max_tokens=2500,   # Allow longer responses for stories
            )
            
            if response and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                return content.strip()
            
            return None
            
        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return None
    
    async def _get_existing_story(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[EventMemory]:
        """Check if a story already exists for this event"""
        try:
            async def _query(session):
                stmt = select(EventMemory).where(
                    and_(
                        EventMemory.user_id == user_id,
                        EventMemory.character_id == character_id,
                        EventMemory.event_type == event_type
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            
            if db_session:
                return await _query(db_session)
            else:
                async with get_db() as session:
                    return await _query(session)
                    
        except Exception as e:
            logger.exception(f"Error checking existing story: {e}")
            return None
    
    async def _save_story(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        story_content: str,
        context_summary: str,
        relationship_state: Optional[Dict[str, Any]],
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[EventMemory]:
        """
        Save generated story to database.
        
        对于 first_* 类型的事件（如 first_date, first_kiss），只保留第一次的记录，不覆盖。
        约会故事的详细内容保存在 date_sessions.story_summary 里，每次约会都有独立记录。
        """
        try:
            async def _save(session):
                # 查找现有记录
                result = await session.execute(
                    select(EventMemory).where(
                        and_(
                            EventMemory.user_id == user_id,
                            EventMemory.character_id == character_id,
                            EventMemory.event_type == event_type,
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                # 对于 first_* 事件，保留第一次的记录，不覆盖
                if existing and event_type.startswith("first_"):
                    logger.info(f"Skipped updating {event_type} (keeping first record): {existing.id}")
                    return existing
                
                # 对于 date 类型，每次都创建新记录（不查重）
                # 其他类型如果存在就更新
                if existing and event_type != "date":
                    existing.story_content = story_content
                    existing.context_summary = context_summary
                    existing.intimacy_level = relationship_state.get("intimacy_stage") if relationship_state else None
                    existing.emotion_state = relationship_state.get("emotion_state") if relationship_state else None
                    existing.generated_at = datetime.utcnow()
                    
                    await session.commit()
                    await session.refresh(existing)
                    
                    logger.info(f"Updated event memory: {existing.id}")
                    return existing
                else:
                    # 插入新记录
                    event_memory = EventMemory(
                        user_id=user_id,
                        character_id=character_id,
                        event_type=event_type,
                        story_content=story_content,
                        context_summary=context_summary,
                        intimacy_level=relationship_state.get("intimacy_stage") if relationship_state else None,
                        emotion_state=relationship_state.get("emotion_state") if relationship_state else None,
                        generated_at=datetime.utcnow(),
                    )
                    
                    session.add(event_memory)
                    await session.commit()
                    await session.refresh(event_memory)
                    
                    logger.info(f"Saved event memory: {event_memory.id}")
                    return event_memory
            
            if db_session:
                return await _save(db_session)
            else:
                async with get_db() as session:
                    return await _save(session)
                    
        except Exception as e:
            logger.exception(f"Error saving story: {e}")
            return None
    
    async def save_story_direct(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        story_content: str,
        context_summary: str = "",
    ) -> Optional[str]:
        """
        直接保存故事到数据库（公开方法）
        
        Returns:
            event_memory_id if success, None otherwise
        """
        result = await self._save_story(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
            story_content=story_content,
            context_summary=context_summary,
            relationship_state=None,
        )
        return result.id if result else None


# =============================================================================
# Singleton Instance
# =============================================================================

event_story_generator = EventStoryGenerator()
