"""
Content Rating System - 集成示例
================================

展示如何将内容分级系统集成到 chat.py 中
"""

# ============================================================================
# 在 chat.py 中的集成方式
# ============================================================================

"""
1. 导入内容分级系统
"""
# from app.services.content_rating_system.content_rating import (
#     content_rating_system, ContentLevel
# )
# from app.services.content_rating_system.content_filter import (
#     content_filter, user_input_filter
# )
# from app.services.content_rating_system.content_prompts import (
#     get_level_prompt, get_rejection_response
# )


async def chat_completion_with_content_rating(request, req, session):
    """示例：带内容分级的聊天完成"""
    
    from app.services.content_rating_system.content_rating import (
        content_rating_system, ContentLevel
    )
    from app.services.content_rating_system.content_filter import (
        content_filter, user_input_filter
    )
    from app.services.content_rating_system.content_prompts import (
        get_level_prompt, get_rejection_response
    )
    
    user_id = "..."  # 从 request 获取
    character_id = session["character_id"]
    intimacy_level = request.intimacy_level
    is_vip = request.is_vip
    
    # =========================================================================
    # Step 1: 检查安全词
    # =========================================================================
    if content_rating_system.check_safe_word(request.message):
        # 用户使用了安全词，立即切换到纯净模式
        return {
            "content": get_rejection_response("safe_word"),
            "mode_changed": True,
            "new_mode": "pure",
        }
    
    # =========================================================================
    # Step 2: 检查用户输入
    # =========================================================================
    user_warning = user_input_filter.should_warn_user(
        request.message, 
        request.content_level or 0
    )
    if user_warning:
        return {
            "content": user_warning,
            "warning": True,
        }
    
    # =========================================================================
    # Step 3: 确定可用的内容等级
    # =========================================================================
    user_setting = ContentLevel(request.content_level) if request.content_level else None
    
    available_level = content_rating_system.get_available_level(
        user_id=user_id,
        character_id=character_id,
        intimacy_level=intimacy_level,
        is_vip=is_vip,
        user_setting=user_setting,
    )
    
    # =========================================================================
    # Step 4: 检查是否需要用户同意
    # =========================================================================
    has_consent, consent_prompt = content_rating_system.check_consent(
        user_id, character_id, available_level
    )
    
    if not has_consent:
        # 需要用户同意才能继续
        return {
            "content": consent_prompt,
            "requires_consent": True,
            "consent_level": available_level.value,
        }
    
    # =========================================================================
    # Step 5: 检查每日限制
    # =========================================================================
    can_continue, remaining = content_rating_system.check_daily_limit(
        user_id, character_id, available_level
    )
    
    if not can_continue:
        return {
            "content": get_rejection_response("cool_down"),
            "daily_limit_reached": True,
        }
    
    # =========================================================================
    # Step 6: 生成内容等级 Prompt
    # =========================================================================
    content_prompt = content_rating_system.generate_content_prompt(
        level=available_level,
        character_name=session["character_name"],
        intimacy_level=intimacy_level,
    )
    
    # 或者使用详细模板
    detailed_prompt = get_level_prompt(available_level)
    
    # =========================================================================
    # Step 7: 构建完整的 System Prompt
    # =========================================================================
    system_prompt = f"""你是 {session['character_name']}...

{emotion_prompt}  # 情绪系统
{memory_prompt}   # 记忆系统

{detailed_prompt}  # 内容分级指令
"""
    
    # =========================================================================
    # Step 8: 调用 LLM
    # =========================================================================
    result = await grok.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            # ... 对话历史
            {"role": "user", "content": request.message},
        ],
        temperature=0.8,
        max_tokens=500,
    )
    
    reply = result["choices"][0]["message"]["content"]
    
    # =========================================================================
    # Step 9: 过滤回复内容
    # =========================================================================
    filter_result = content_filter.filter(reply, available_level.value)
    
    if filter_result.was_modified:
        logger.warning(f"Content was filtered: {filter_result.violations}")
        reply = filter_result.filtered
    
    # 如果过滤后的内容太短或有严重违规，重新生成
    if filter_result.severity == 'critical' or len(reply) < 10:
        # 重新生成一个安全的回复
        reply = await regenerate_safe_response(
            session, request.message, available_level
        )
    
    # =========================================================================
    # Step 10: 记录使用
    # =========================================================================
    content_rating_system.record_usage(user_id, character_id, available_level)
    
    return {
        "content": reply,
        "content_level": available_level.value,
        "content_level_name": available_level.name,
    }


async def handle_consent_response(request, req, session):
    """处理用户同意/拒绝的响应"""
    
    from app.services.content_rating_system.content_rating import (
        content_rating_system, ContentLevel
    )
    
    user_id = get_user_id(req)
    character_id = session["character_id"]
    level = ContentLevel(request.consent_level)
    consented = request.user_consented  # True / False
    
    # 记录用户选择
    content_rating_system.record_consent(user_id, character_id, level, consented)
    
    if consented:
        return {
            "content": f"好的～那我们继续吧！💕",
            "mode_unlocked": level.name,
        }
    else:
        return {
            "content": "没关系的，我们可以慢慢来～",
            "mode_kept": "current",
        }


# ============================================================================
# API 端点示例
# ============================================================================

"""
# content_routes.py

from fastapi import APIRouter, Request
from uuid import UUID

router = APIRouter(prefix="/content")

@router.get("/settings/{character_id}")
async def get_content_settings(character_id: UUID, request: Request):
    '''获取内容设置'''
    user_id = get_user_id(request)
    
    # 获取用户的内容等级设置
    settings = await get_user_content_settings(user_id, str(character_id))
    
    # 获取可用等级
    available_level = content_rating_system.get_available_level(
        user_id=user_id,
        character_id=str(character_id),
        intimacy_level=settings.get("intimacy_level", 1),
        is_vip=settings.get("is_vip", False),
    )
    
    return {
        "current_level": settings.get("content_level", 0),
        "available_level": available_level.value,
        "available_level_name": available_level.name,
        "levels": [
            {
                "level": level.value,
                "name": config.name_cn,
                "description": config.description,
                "min_intimacy": config.min_intimacy,
                "requires_vip": config.requires_vip,
                "unlocked": level.value <= available_level.value,
            }
            for level, config in CONTENT_LEVELS.items()
        ]
    }

@router.post("/settings/{character_id}")
async def update_content_settings(
    character_id: UUID, 
    settings: ContentSettingsUpdate,
    request: Request
):
    '''更新内容设置'''
    user_id = get_user_id(request)
    
    # 验证等级是否可用
    available = content_rating_system.get_available_level(...)
    
    if settings.level > available.value:
        raise HTTPException(400, "该内容等级尚未解锁")
    
    # 保存设置
    await save_user_content_settings(user_id, str(character_id), {
        "content_level": settings.level,
    })
    
    return {"success": True}
"""


# ============================================================================
# 前端集成建议
# ============================================================================

"""
1. 内容等级选择器 UI

┌─────────────────────────────────────────────────────────────┐
│  🔒 内容模式设置                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ○ 纯净模式                           [已解锁]              │
│    友好日常对话                                              │
│                                                              │
│  ○ 暧昧模式                           [已解锁]              │
│    轻度调情，偶像剧风格                亲密度 15+            │
│                                                              │
│  ○ 亲密模式                           [当前]  ✓             │
│    拥抱牵手等温馨互动                  亲密度 30+            │
│                                                              │
│  ○ 浪漫模式                           [需要 VIP]            │
│    浪漫氛围，亲吻描写                  亲密度 50+ & VIP      │
│                                                              │
│  ○ 热恋模式                           [🔒 未解锁]           │
│    暧昧暗示，留白想象                  亲密度 80+ & VIP      │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  ⚠️ 安全提示：                                              │
│  • 你随时可以说「停」来结束亲密对话                         │
│  • 热恋模式需要年龄验证                                      │
│                                                              │
│                                        [保存设置]           │
└─────────────────────────────────────────────────────────────┘


2. 同意确认弹窗

┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  💕 解锁新模式                                               │
│                                                              │
│  你们的关系更进一步了！                                      │
│  要解锁「亲密模式」吗？                                      │
│                                                              │
│  这意味着对话中可能出现：                                    │
│  • 拥抱、牵手等描写                                          │
│  • 更亲密的情感表达                                          │
│                                                              │
│  你随时可以说「停」来退出这个模式                           │
│                                                              │
│        [解锁] [保持现在的模式]                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘


3. 等级指示器（聊天界面）

┌─────────────────────────────────────────────────────────────┐
│  小美                                    💕 亲密模式         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [对话内容...]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
"""


# ============================================================================
# App Store 审核注意事项
# ============================================================================

"""
为了通过 App Store 审核，请确保：

1. 【年龄分级】
   - App 应标记为 17+ 
   - 热恋模式需要年龄验证
   - 在 App 描述中说明包含"轻度成人主题"

2. 【用户控制】
   - 默认使用纯净模式
   - 用户必须主动选择开启更高等级
   - 提供明显的退出/降级选项
   - 安全词功能必须有效

3. 【内容限制】
   - 任何等级都不能出现绝对禁止词汇
   - 最高等级也只能是暗示和留白
   - 所有生成内容必须经过过滤器

4. 【审核材料】
   - 准备演示账号展示所有等级
   - 准备说明文档解释内容分级系统
   - 说明过滤机制如何工作

5. 【地区限制】
   - 某些地区可能需要完全禁用高等级内容
   - 准备好地区配置开关
"""
