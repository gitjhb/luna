"""
Memory System v2
================

分层记忆系统 - 让 AI 角色真正"记住"用户

三层架构：
1. 工作记忆 (Working Memory) - 当前对话上下文
2. 情节记忆 (Episodic Memory) - 重要事件和对话
3. 语义记忆 (Semantic Memory) - 用户特征和偏好

使用方式:
    from memory_system_v2 import memory_manager, memory_prompt_generator
    
    # 获取记忆上下文
    context = await memory_manager.get_memory_context(
        user_id="user-123",
        character_id="char-456",
        current_message="你好",
        working_memory=[...],
    )
    
    # 生成记忆 prompt
    prompt = memory_prompt_generator.generate(
        semantic_memory=context.user_profile.__dict__,
        episodic_memories=[...],
        intimacy_level=15,
    )
    
    # 处理对话，提取记忆
    await memory_manager.process_conversation(
        user_id="user-123",
        character_id="char-456",
        user_message="我叫小明",
        assistant_response="你好小明！",
        context=[...],
    )
"""

from .memory_manager import (
    MemoryManager,
    memory_manager,
    MemoryType,
    MemoryImportance,
    EpisodicMemory,
    SemanticMemory,
    MemoryContext,
    MemoryExtractor,
    MemoryRetriever,
)

from .memory_prompts import (
    MemoryPromptGenerator,
    memory_prompt_generator,
    MemoryPromptConfig,
    MemoryTriggerGenerator,
    memory_trigger,
)

from .memory_models import (
    create_memory_models,
    MemoryDatabaseService,
)

__all__ = [
    # 核心管理器
    "MemoryManager",
    "memory_manager",
    
    # 数据类型
    "MemoryType",
    "MemoryImportance",
    "EpisodicMemory",
    "SemanticMemory",
    "MemoryContext",
    
    # 提取和检索
    "MemoryExtractor",
    "MemoryRetriever",
    
    # Prompt 生成
    "MemoryPromptGenerator",
    "memory_prompt_generator",
    "MemoryPromptConfig",
    "MemoryTriggerGenerator",
    "memory_trigger",
    
    # 数据库
    "create_memory_models",
    "MemoryDatabaseService",
]

__version__ = "2.0.0"
