"""
Emotion Engine v2
=================

智能情绪系统 - 让 AI 角色有真实的情感反应

特性:
- 三层分析: 快速检测 + LLM 深度分析 + 状态机管理
- 情绪缓冲: 不会一句话暴怒
- 自然冷却: 时间治愈一切
- 礼物机制: 可以解除冷战

使用方式:
    from emotion_engine_v2 import emotion_engine, emotion_prompt_generator
    
    # 处理消息
    result = await emotion_engine.process_message(
        user_id="user-123",
        character_id="char-456",
        message="我爱你",
        context=[...],
        intimacy_level=15,
    )
    
    # 生成情绪 prompt
    prompt = emotion_prompt_generator.generate(
        state=EmotionState.HAPPY,
        score=75,
        character_name="小美",
        intimacy_level=15,
    )
"""

from .emotion_engine import (
    EmotionEngineV2,
    emotion_engine,
    EmotionState,
    EmotionAnalysis,
    EmotionBuffer,
    CharacterPersonality,
)

from .emotion_prompts import (
    EmotionPromptGenerator,
    emotion_prompt_generator,
    EmotionPromptConfig,
    EMOTION_PROMPTS,
)

from .emotion_models import (
    create_emotion_models,
    EmotionDatabaseService,
)

__all__ = [
    # 核心引擎
    "EmotionEngineV2",
    "emotion_engine",
    
    # 数据类型
    "EmotionState",
    "EmotionAnalysis",
    "EmotionBuffer",
    "CharacterPersonality",
    
    # Prompt 生成
    "EmotionPromptGenerator",
    "emotion_prompt_generator",
    "EmotionPromptConfig",
    "EMOTION_PROMPTS",
    
    # 数据库
    "create_emotion_models",
    "EmotionDatabaseService",
]

__version__ = "2.0.0"
