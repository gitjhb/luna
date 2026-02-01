"""
Emotion Engine v2 - 集成示例
============================

展示如何将新的情绪引擎集成到现有的 chat.py 中
"""

# ============================================================================
# 在 chat.py 中的集成方式
# ============================================================================

"""
1. 导入新的情绪引擎
"""
# from app.services.emotion_engine_v2.emotion_engine import emotion_engine, CharacterPersonality
# from app.services.emotion_engine_v2.emotion_prompts import emotion_prompt_generator, EmotionState

"""
2. 替换原有的情绪处理代码
"""

# 原代码位置: chat.py 第 225-330 行
# 替换为:

async def process_emotion_v2(
    user_id: str,
    character_id: str,
    message: str,
    context: list,
    intimacy_level: int,
    character_data: dict,
):
    """
    使用 Emotion Engine v2 处理情绪
    
    返回:
    {
        "emotion_prompt": str,          # 添加到 system prompt 的情绪指令
        "is_blocked": bool,             # 是否被拉黑
        "is_cold_war": bool,            # 是否在冷战
        "llm_modifiers": dict,          # LLM 参数修改
        "special_response": str | None, # 特殊状态的固定回复
    }
    """
    from app.services.emotion_engine_v2.emotion_engine import (
        emotion_engine, CharacterPersonality, EmotionState
    )
    from app.services.emotion_engine_v2.emotion_prompts import emotion_prompt_generator
    
    # 构建角色性格
    character = CharacterPersonality(
        name=character_data.get("name", "AI Companion"),
        base_temperament=character_data.get("temperament", "cheerful"),
        sensitivity=character_data.get("sensitivity", 0.5),
        forgiveness_rate=character_data.get("forgiveness_rate", 0.6),
        jealousy_level=character_data.get("jealousy_level", 0.3),
        love_triggers=character_data.get("love_triggers", []),
        hate_triggers=character_data.get("hate_triggers", []),
        soft_spots=character_data.get("soft_spots", []),
    )
    
    # 处理消息，更新情绪
    result = await emotion_engine.process_message(
        user_id=user_id,
        character_id=character_id,
        message=message,
        context=context,
        character=character,
        intimacy_level=intimacy_level,
    )
    
    # 获取当前状态
    current_score = result["new_score"]
    current_state = EmotionState(result["new_state"])
    
    # 检查是否被拉黑
    if current_state == EmotionState.BLOCKED:
        return {
            "emotion_prompt": "",
            "is_blocked": True,
            "is_cold_war": False,
            "llm_modifiers": {"skip_llm": True},
            "special_response": f"[系统提示] {character.name}已将你删除好友，无法发送消息。",
            "can_recover": True,
            "recovery_hint": "送「真诚道歉礼盒」或许能挽回？",
        }
    
    # 生成情绪 Prompt
    emotion_prompt = emotion_prompt_generator.generate(
        state=current_state,
        score=current_score,
        character_name=character.name,
        intimacy_level=intimacy_level,
        recent_trigger=result["analysis"].get("reasoning"),
    )
    
    # 获取 LLM 参数修改
    llm_modifiers = emotion_prompt_generator.get_response_modifier(
        current_state, current_score
    )
    
    # 冷战状态的特殊处理
    is_cold_war = current_state == EmotionState.COLD_WAR
    special_response = None
    
    if is_cold_war and result.get("cold_war_hint"):
        # 冷战时如果有道歉，给一点回应
        special_response = result.get("cold_war_hint")
    
    return {
        "emotion_prompt": emotion_prompt,
        "is_blocked": False,
        "is_cold_war": is_cold_war,
        "llm_modifiers": llm_modifiers,
        "special_response": special_response,
        "emotion_data": {
            "score": current_score,
            "state": current_state.value,
            "delta": result["delta_applied"],
            "analysis": result["analysis"],
        },
    }


"""
3. 修改 chat_completion 函数
"""

# 在调用 Grok API 之前，处理情绪：

async def chat_completion_with_emotion_v2(request, req, session):
    """示例：带情绪系统的聊天完成"""
    
    user_id = "..."  # 从 request 获取
    character_id = session["character_id"]
    character_data = {}  # 从数据库获取角色配置
    
    # 获取对话历史
    all_messages = await chat_repo.get_all_messages(session["session_id"])
    context = [{"role": m["role"], "content": m["content"]} for m in all_messages[-10:]]
    
    # 处理情绪
    emotion_result = await process_emotion_v2(
        user_id=user_id,
        character_id=character_id,
        message=request.message,
        context=context,
        intimacy_level=request.intimacy_level,
        character_data=character_data,
    )
    
    # 检查是否被拉黑
    if emotion_result["is_blocked"]:
        return {
            "content": emotion_result["special_response"],
            "blocked": True,
            "recovery_hint": emotion_result.get("recovery_hint"),
        }
    
    # 检查是否跳过 LLM（冷战时可能直接返回固定回复）
    if emotion_result["llm_modifiers"].get("skip_llm"):
        return {
            "content": emotion_result.get("special_response", "..."),
        }
    
    # 构建 system prompt（包含情绪指令）
    system_prompt = f"""你是 {session['character_name']}...
    
{emotion_result['emotion_prompt']}
"""
    
    # 调用 LLM（使用修改后的参数）
    llm_params = {
        "temperature": emotion_result["llm_modifiers"].get("temperature", 0.7),
        "max_tokens": emotion_result["llm_modifiers"].get("max_tokens", 400),
    }
    
    # ... 调用 Grok API ...
    
    return {
        "content": "...",  # LLM 返回
        "emotion": emotion_result["emotion_data"],
    }


# ============================================================================
# 礼物效果处理
# ============================================================================

async def apply_gift_with_emotion_v2(
    user_id: str,
    character_id: str,
    gift_id: str,
    gift_type: str,  # small / medium / large / special
    gift_value: int,  # 礼物价值（金币）
):
    """
    应用礼物效果到情绪系统
    
    返回角色反应和新的情绪状态
    """
    from app.services.emotion_engine_v2.emotion_engine import emotion_engine
    
    result = await emotion_engine.apply_gift_effect(
        user_id=user_id,
        character_id=character_id,
        gift_type=gift_type,
        gift_value=gift_value,
    )
    
    return {
        "success": result["success"],
        "character_reaction": result.get("character_reaction", "谢谢～"),
        "new_score": result.get("new_score"),
        "new_state": result.get("new_state"),
        "cold_war_resolved": result.get("cold_war_resolved", False),
        "blocked_resolved": result.get("blocked_resolved", False),
    }


# ============================================================================
# 自然冷却（定时任务）
# ============================================================================

async def run_emotion_decay():
    """
    定期运行的情绪冷却任务
    
    建议每小时运行一次
    """
    from app.services.emotion_engine_v2.emotion_engine import emotion_engine
    from datetime import datetime, timedelta
    
    # 获取所有需要冷却的用户-角色组合
    # 这里需要从数据库查询最近有互动的记录
    active_pairs = []  # [(user_id, character_id, last_interaction_time), ...]
    
    now = datetime.now()
    
    for user_id, character_id, last_time in active_pairs:
        hours_passed = (now - last_time).total_seconds() / 3600
        
        if hours_passed >= 1:  # 至少 1 小时才应用冷却
            await emotion_engine.apply_natural_decay(
                user_id=user_id,
                character_id=character_id,
                hours_passed=hours_passed,
            )


# ============================================================================
# API 端点示例
# ============================================================================

"""
# emotion_routes.py

from fastapi import APIRouter, Request
from uuid import UUID

router = APIRouter(prefix="/emotion/v2")

@router.get("/{character_id}")
async def get_emotion_status(character_id: UUID, request: Request):
    '''获取情绪状态（使用新引擎）'''
    from app.services.emotion_engine_v2.emotion_engine import emotion_engine
    
    user_id = get_user_id(request)
    
    score = await emotion_engine.get_score(user_id, str(character_id))
    state = emotion_engine.score_to_state(score)
    
    return {
        "score": score,
        "state": state.value,
        "state_description": get_state_description(state),
        "can_recover": score <= -80,  # 冷战或拉黑
    }

@router.post("/{character_id}/gift")
async def send_gift(character_id: UUID, gift_data: GiftRequest, request: Request):
    '''送礼物'''
    user_id = get_user_id(request)
    
    result = await apply_gift_with_emotion_v2(
        user_id=user_id,
        character_id=str(character_id),
        gift_id=gift_data.gift_id,
        gift_type=gift_data.gift_type,
        gift_value=gift_data.gift_value,
    )
    
    return result

@router.get("/{character_id}/history")
async def get_emotion_history(character_id: UUID, request: Request, limit: int = 20):
    '''获取情绪变化历史'''
    from app.services.emotion_engine_v2.emotion_models import EmotionDatabaseService
    
    user_id = get_user_id(request)
    db_service = EmotionDatabaseService(get_session)
    
    history = await db_service.get_emotion_history(
        user_id=user_id,
        character_id=str(character_id),
        limit=limit,
    )
    
    return {"history": history}
"""


# ============================================================================
# 前端状态展示建议
# ============================================================================

"""
根据情绪分数，前端可以展示不同的 UI：

score >= 80:  ❤️❤️❤️❤️❤️  "深爱"  - 红色心形，跳动动画
score >= 50:  ❤️❤️❤️❤️    "开心"  - 粉色心形
score >= 20:  💛💛💛       "满意"  - 黄色心形
score >= -19: 💙💙         "普通"  - 蓝色心形
score >= -49: 💔           "不悦"  - 破碎心形，灰色
score >= -79: 😤           "生气"  - 生气表情
score >= -99: 🥶           "冷战"  - 冰冻效果，头像变灰
score = -100: 🚫           "拉黑"  - 禁止符号，无法发送消息

冷战/拉黑状态下显示：
- "送礼物" 按钮高亮
- 提示文字："或许一份礼物能缓和关系？"
- 特殊礼物（真诚道歉礼盒）在商店中突出显示
"""
