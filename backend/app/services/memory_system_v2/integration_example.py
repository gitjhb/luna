"""
Memory System v2 - 集成示例
============================

展示如何将记忆系统集成到现有的 chat.py 中
"""

# ============================================================================
# 在 chat.py 中的集成方式
# ============================================================================

"""
1. 导入记忆系统
"""
# from app.services.memory_system_v2.memory_manager import memory_manager
# from app.services.memory_system_v2.memory_prompts import memory_prompt_generator, memory_trigger

"""
2. 修改 chat_completion 函数
"""

async def chat_completion_with_memory(request, req, session):
    """示例：带记忆系统的聊天完成"""
    
    user_id = "..."  # 从 request 获取
    character_id = session["character_id"]
    
    # 获取工作记忆（最近的对话）
    all_messages = await chat_repo.get_all_messages(session["session_id"])
    working_memory = [
        {"role": m["role"], "content": m["content"]}
        for m in all_messages[-15:]  # 最近 15 条
    ]
    
    # =========================================================================
    # 新增：获取记忆上下文
    # =========================================================================
    from app.services.memory_system_v2.memory_manager import memory_manager
    from app.services.memory_system_v2.memory_prompts import memory_prompt_generator
    
    memory_context = await memory_manager.get_memory_context(
        user_id=user_id,
        character_id=character_id,
        current_message=request.message,
        working_memory=working_memory,
    )
    
    # 生成记忆 prompt
    memory_prompt = memory_prompt_generator.generate(
        semantic_memory=memory_context.user_profile.__dict__ if memory_context.user_profile else {},
        episodic_memories=[ep.__dict__ for ep in memory_context.relevant_episodes + memory_context.recent_episodes],
        current_query=request.message,
        intimacy_level=request.intimacy_level,
    )
    
    # =========================================================================
    # 构建 system prompt（包含记忆）
    # =========================================================================
    system_prompt = f"""你是 {session['character_name']}...

{memory_prompt}

{emotion_prompt}  # 情绪系统的 prompt
"""
    
    # 调用 LLM
    conversation = [{"role": "system", "content": system_prompt}]
    conversation.extend(working_memory)
    conversation.append({"role": "user", "content": request.message})
    
    result = await grok.chat_completion(
        messages=conversation,
        temperature=0.8,
        max_tokens=500,
    )
    
    reply = result["choices"][0]["message"]["content"]
    
    # =========================================================================
    # 新增：处理记忆提取
    # =========================================================================
    await memory_manager.process_conversation(
        user_id=user_id,
        character_id=character_id,
        user_message=request.message,
        assistant_response=reply,
        context=working_memory,
    )
    
    return {"content": reply}


"""
3. 定时任务：记忆衰减
"""

async def daily_memory_decay():
    """
    每日运行的记忆衰减任务
    """
    from app.services.memory_system_v2.memory_manager import memory_manager
    
    # 获取所有用户-角色组合
    active_pairs = []  # [(user_id, character_id), ...]
    
    for user_id, character_id in active_pairs:
        await memory_manager.apply_memory_decay(
            user_id=user_id,
            character_id=character_id,
            days_passed=1.0,
        )


# ============================================================================
# API 端点示例
# ============================================================================

"""
# memory_routes.py

from fastapi import APIRouter, Request
from uuid import UUID

router = APIRouter(prefix="/memory")

@router.get("/{character_id}/profile")
async def get_user_profile(character_id: UUID, request: Request):
    '''获取用户档案（语义记忆）'''
    from app.services.memory_system_v2.memory_manager import memory_manager
    
    user_id = get_user_id(request)
    
    semantic = await memory_manager.get_semantic_memory(
        user_id=user_id,
        character_id=str(character_id),
    )
    
    return {
        "profile": semantic.__dict__ if semantic else {},
    }

@router.get("/{character_id}/episodes")
async def get_memory_episodes(character_id: UUID, request: Request, limit: int = 20):
    '''获取情节记忆列表'''
    from app.services.memory_system_v2.memory_manager import memory_manager
    
    user_id = get_user_id(request)
    
    episodes = await memory_manager.get_episodic_memories(
        user_id=user_id,
        character_id=str(character_id),
    )
    
    return {
        "episodes": [
            {
                "event_type": ep.event_type,
                "summary": ep.summary,
                "importance": ep.importance.value,
                "created_at": ep.created_at.isoformat(),
            }
            for ep in episodes[:limit]
        ],
    }

@router.post("/{character_id}/profile")
async def update_user_profile(character_id: UUID, updates: dict, request: Request):
    '''手动更新用户档案'''
    from app.services.memory_system_v2.memory_manager import memory_manager
    
    user_id = get_user_id(request)
    
    # 获取当前档案
    semantic = await memory_manager.get_semantic_memory(user_id, str(character_id))
    
    # 应用更新
    await memory_manager._update_semantic(
        user_id=user_id,
        character_id=str(character_id),
        updates=updates,
    )
    
    return {"success": True}
"""


# ============================================================================
# 使用场景示例
# ============================================================================

"""
场景 1: 用户说 "我叫小明"
--------------------------------------------------
Memory Extractor 检测到 name 模式
  → 更新 semantic_memory.user_name = "小明"
  → 下次对话 AI 会用 "小明" 称呼用户

场景 2: 用户说 "我爱你"（第一次）
--------------------------------------------------
Memory Extractor 检测到 confession 事件
  → 创建 episodic_memory:
    - event_type: "confession"
    - summary: "用户第一次对你说爱你"
    - importance: CRITICAL (4)
  → 这个记忆会被长期保存
  → AI 可以在未来提及 "还记得你第一次说爱我的时候吗？"

场景 3: 用户生日当天
--------------------------------------------------
Memory Prompt Generator 检测到今天是特殊日期
  → 在 system prompt 中添加：
    "⭐ 今天特殊提醒: 今天是小明的生日！一定要祝福！"
  → AI 会主动说 "生日快乐！"

场景 4: 用户问 "你还记得我喜欢什么吗？"
--------------------------------------------------
Memory Retriever 搜索相关记忆
  → 找到 semantic_memory.likes = ["猫", "动漫", "拉面"]
  → AI 可以回答 "当然记得，你喜欢猫咪、看动漫，还有...好像是拉面？"
"""


# ============================================================================
# 前端展示建议
# ============================================================================

"""
记忆卡片展示:
┌─────────────────────────────────────┐
│  📝 你们的回忆                       │
├─────────────────────────────────────┤
│  💕 第一次表白  [重要]               │
│     2024-03-15                       │
│     "我...我喜欢你，做我女朋友吧"    │
├─────────────────────────────────────┤
│  🎁 收到礼物                         │
│     2024-03-20                       │
│     "情人节的玫瑰花"                 │
├─────────────────────────────────────┤
│  🎉 一周年纪念  [里程碑]             │
│     2025-03-15                       │
│     "我们在一起一年了！"             │
└─────────────────────────────────────┘

用户档案展示:
┌─────────────────────────────────────┐
│  👤 关于你                           │
├─────────────────────────────────────┤
│  名字: 小明                          │
│  生日: 2月14日 ❤️                    │
│  职业: 程序员                        │
├─────────────────────────────────────┤
│  喜欢: 猫、动漫、拉面、游戏          │
│  不喜欢: 香菜、加班                  │
├─────────────────────────────────────┤
│  你的昵称: 宝贝、小笨蛋              │
│  纪念日: 3月15日                     │
└─────────────────────────────────────┘
"""
