"""
Memory Integration Service
==========================

Integrates the memory system v2 with chat completions.
This is the main entry point for using the memory system.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Import memory system components
from app.services.memory_system_v2 import (
    MemoryManager,
    memory_prompt_generator,
    MemoryContext,
)
from app.services.memory_db_service import memory_db_service

# Global memory manager instance (initialized lazily)
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """
    Get the initialized memory manager.
    
    Lazy initialization ensures DB service is available.
    """
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager(
            db_service=memory_db_service,
            llm_service=None,  # LLM extraction is optional
        )
        logger.info("Memory manager initialized with DB service")
    
    return _memory_manager


async def get_memory_context_for_chat(
    user_id: str,
    character_id: str,
    current_message: str,
    working_memory: List[Dict[str, str]],
) -> Optional[MemoryContext]:
    """
    Get memory context for a chat completion.
    
    This should be called before generating the LLM response
    to include relevant memories in the context.
    
    Args:
        user_id: User UUID as string
        character_id: Character UUID as string
        current_message: The current user message
        working_memory: Recent conversation messages
    
    Returns:
        MemoryContext or None if failed
    """
    try:
        manager = get_memory_manager()
        context = await manager.get_memory_context(
            user_id=user_id,
            character_id=character_id,
            current_message=current_message,
            working_memory=working_memory,
        )
        logger.debug(f"Got memory context for user={user_id}, char={character_id}")
        return context
    except Exception as e:
        logger.error(f"Failed to get memory context: {e}")
        return None


async def process_conversation_for_memory(
    user_id: str,
    character_id: str,
    user_message: str,
    assistant_response: str,
    context: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Process a conversation to extract and store memories.
    
    This should be called after the LLM response is generated
    to capture any new information from the conversation.
    
    Args:
        user_id: User UUID as string
        character_id: Character UUID as string
        user_message: The user's message
        assistant_response: The AI's response
        context: Conversation context
    
    Returns:
        Dict with extraction results
    """
    try:
        manager = get_memory_manager()
        result = await manager.process_conversation(
            user_id=user_id,
            character_id=character_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=context,
        )
        
        if result.get("semantic_updated") or result.get("episodic_created"):
            logger.info(
                f"Memory extracted: user={user_id}, semantic={result.get('semantic_updated')}, "
                f"episodic={result.get('episodic_created')}"
            )
        
        return result
    except Exception as e:
        logger.error(f"Failed to process conversation for memory: {e}")
        return {"semantic_updated": False, "episodic_created": False, "error": str(e)}


def generate_memory_prompt(
    memory_context: MemoryContext,
    intimacy_level: int = 1,
    current_query: str = "",
) -> str:
    """
    Generate the memory portion of the system prompt.
    
    This creates a natural language description of what the AI
    should remember about the user.
    
    Args:
        memory_context: MemoryContext from get_memory_context_for_chat
        intimacy_level: Current relationship level (1-100)
        current_query: Current user message for relevance
    
    Returns:
        String to include in system prompt
    """
    try:
        # Convert dataclasses to dicts for the prompt generator
        semantic_dict = {}
        if memory_context.user_profile:
            profile = memory_context.user_profile
            semantic_dict = {
                "user_name": profile.user_name,
                "user_nickname": profile.user_nickname,
                "birthday": profile.birthday,
                "occupation": profile.occupation,
                "location": profile.location,
                "likes": profile.likes,
                "dislikes": profile.dislikes,
                "interests": profile.interests,
                "personality_traits": profile.personality_traits,
                "communication_style": profile.communication_style,
                "relationship_status": profile.relationship_status,
                "pet_names": profile.pet_names,
                "important_dates": profile.important_dates,
                "shared_jokes": profile.shared_jokes,
                "sensitive_topics": profile.sensitive_topics,
            }
        
        episodic_list = []
        for ep in memory_context.relevant_episodes + memory_context.recent_episodes:
            episodic_list.append({
                "event_type": ep.event_type,
                "summary": ep.summary,
                "key_dialogue": ep.key_dialogue,
                "importance": ep.importance.value if hasattr(ep.importance, 'value') else ep.importance,
                "strength": ep.strength,
                "created_at": ep.created_at.isoformat() if ep.created_at else None,
                "last_recalled": ep.last_recalled.isoformat() if ep.last_recalled else None,
            })
        
        prompt = memory_prompt_generator.generate(
            semantic_memory=semantic_dict,
            episodic_memories=episodic_list,
            current_query=current_query,
            intimacy_level=intimacy_level,
        )
        
        # Add special date reminder if exists
        if memory_context.today_special:
            prompt = f"⭐ {memory_context.today_special}\n\n" + prompt
        
        return prompt
    except Exception as e:
        logger.error(f"Failed to generate memory prompt: {e}")
        return ""


async def apply_daily_decay(
    user_id: str,
    character_id: str,
    days_passed: float = 1.0,
) -> None:
    """
    Apply memory decay for a user-character pair.
    
    Should be called daily via cron job or periodic task.
    """
    try:
        manager = get_memory_manager()
        await manager.apply_memory_decay(
            user_id=user_id,
            character_id=character_id,
            days_passed=days_passed,
        )
        logger.info(f"Applied memory decay for user={user_id}, char={character_id}")
    except Exception as e:
        logger.error(f"Failed to apply memory decay: {e}")
