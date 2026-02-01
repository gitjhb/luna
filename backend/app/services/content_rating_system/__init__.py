"""
Content Rating System - 渐进式内容分级
=====================================

符合 App Store 审核的内容分级系统

设计原则：
1. 渐进解锁 - 随亲密度和VIP状态解锁
2. 留白艺术 - 暧昧但不露骨
3. 用户可控 - 安全词、随时退出
4. 审核友好 - 过滤违规内容

内容等级：
- Level 0: 纯净模式 (Pure) - 友好日常
- Level 1: 暧昧模式 (Flirty) - 轻度调情
- Level 2: 亲密模式 (Intimate) - 拥抱牵手
- Level 3: 浪漫模式 (Romantic) - 亲吻相拥
- Level 4: 热恋模式 (Passionate) - 暗示留白

使用方式:
    from content_rating_system import (
        content_rating_system, ContentLevel,
        content_filter, get_level_prompt
    )
    
    # 获取可用等级
    level = content_rating_system.get_available_level(
        user_id, character_id,
        intimacy_level=30, is_vip=True
    )
    
    # 生成内容 prompt
    prompt = content_rating_system.generate_content_prompt(
        level=level,
        character_name="小美",
        intimacy_level=30,
    )
    
    # 过滤 AI 回复
    result = content_filter.filter(ai_response, level.value)
"""

from .content_rating import (
    ContentRatingSystem,
    content_rating_system,
    ContentLevel,
    ContentLevelConfig,
    SafetyConfig,
    CONTENT_LEVELS,
)

from .content_filter import (
    ContentFilter,
    content_filter,
    UserInputFilter,
    user_input_filter,
    FilterResult,
)

from .content_prompts import (
    LEVEL_PROMPTS,
    SCENARIO_TEMPLATES,
    REJECTION_TEMPLATES,
    get_level_prompt,
    get_scenario_response,
    get_rejection_response,
)

__all__ = [
    # 核心系统
    "ContentRatingSystem",
    "content_rating_system",
    
    # 等级相关
    "ContentLevel",
    "ContentLevelConfig",
    "CONTENT_LEVELS",
    
    # 安全配置
    "SafetyConfig",
    
    # 过滤器
    "ContentFilter",
    "content_filter",
    "UserInputFilter",
    "user_input_filter",
    "FilterResult",
    
    # Prompt 模板
    "LEVEL_PROMPTS",
    "SCENARIO_TEMPLATES",
    "REJECTION_TEMPLATES",
    "get_level_prompt",
    "get_scenario_response",
    "get_rejection_response",
]

__version__ = "1.0.0"
