"""
Chat Pipeline v4.0 - Single Call Architecture
=============================================

V4.0单次调用流水线：
Service前置计算 → Prompt Builder → 单次LLM调用(JSON) → 异步后置更新 → Response
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.core.perf import PerfTracker
from app.services.v4.precompute_service import precompute_service, PrecomputeResult
from app.services.v4.prompt_builder_v4 import prompt_builder_v4
from app.services.v4.json_parser import json_parser, ParsedResponse
from app.services.llm_service import GrokService
from app.services.chat_repository import chat_repo

logger = logging.getLogger(__name__)


@dataclass
class UserStateV4:
    """简化的用户状态 (用于V4)"""
    user_id: str
    character_id: str
    intimacy_level: int = 1
    intimacy_x: float = 0.0  # 0-100的亲密度值
    emotion: int = 0         # -100 to 100
    events: List[str] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        
        # 如果没有提供intimacy_x，从level计算
        if self.intimacy_x == 0.0:
            self.intimacy_x = self._level_to_intimacy(self.intimacy_level)
    
    def _level_to_intimacy(self, level: int) -> float:
        """将等级映射到intimacy值"""
        if level <= 5:
            return (level - 1) * 4.75
        elif level <= 10:
            return 20 + (level - 6) * 4
        elif level <= 15:
            return 40 + (level - 11) * 4
        elif level <= 25:
            return 60 + (level - 16) * 2
        else:
            return min(100, 80 + (level - 26) * 1.4)


@dataclass
class ChatRequestV4:
    """V4聊天请求"""
    user_id: str
    character_id: str
    session_id: str
    message: str
    intimacy_level: int = 1
    client_message_id: Optional[str] = None  # Client-generated UUID for user message dedup


@dataclass
class ChatResponseV4:
    """V4聊天响应"""
    message_id: str
    content: str
    tokens_used: int
    character_name: str
    extra_data: Dict[str, Any] = None
    
    # V4新增字段
    emotion_delta: int = 0
    intent: str = "SMALL_TALK"
    is_nsfw_blocked: bool = False
    thought: str = ""
    parse_success: bool = True
    parse_error: str = ""


class ChatPipelineV4:
    """V4.0聊天流水线"""
    
    def __init__(self):
        self.grok_service = GrokService()
    
    async def process_message(self, request: ChatRequestV4) -> ChatResponseV4:
        """
        处理聊天消息的主流程
        
        Args:
            request: 聊天请求
            
        Returns:
            聊天响应
        """
        perf = PerfTracker()
        
        try:
            # 1. 加载用户状态
            async with perf.track_async("load_state"):
                user_state = await self._load_user_state(request.user_id, request.character_id)
            logger.info(f"📊 User State: level={user_state.intimacy_level}, "
                       f"intimacy={user_state.intimacy_x:.1f}, emotion={user_state.emotion}")
            
            # 2. 前置计算 (替代L1)
            with perf.track("precompute"):
                precompute_result = precompute_service.analyze(
                    message=request.message,
                    user_state=user_state
                )
            logger.info(f"📊 Precompute: {precompute_service.get_analysis_summary(precompute_result)}")
            
            # 3. 硬性拦截检查
            if precompute_result.safety_flag == "BLOCK":
                return self._create_blocked_response("系统拦截：内容违规")
            
            # 4. 检查情绪锁定状态
            if user_state.emotion <= -75:  # 冷战状态
                return self._create_cold_war_response(user_state, precompute_result)
            
            # 5. 获取对话上下文
            async with perf.track_async("db_context"):
                context_messages = await self._get_context_messages(request.session_id)
            
            # 5.5 先存用户消息（确保 DB 立即可查，避免前端 refetch 时消息消失）
            async with perf.track_async("db_save_user"):
                await chat_repo.add_message(
                    session_id=request.session_id,
                    role="user",
                    content=request.message,
                    tokens_used=0,
                    message_id=request.client_message_id,  # Use client-provided ID if available
                )
            
            # 5.6 获取用户兴趣
            user_interests = await self._load_user_interests(request.user_id)
            
            # 5.7 获取记忆上下文
            async with perf.track_async("memory"):
                memory_context_str = await self._load_memory_context(
                    request.user_id, request.character_id,
                    request.message, context_messages,
                    getattr(user_state, 'intimacy_level', 1)
                )
            
            # 5.8 获取礼物记忆
            gift_memory_str = await self._load_gift_memory(
                request.user_id, request.character_id
            )
            if gift_memory_str:
                if memory_context_str:
                    memory_context_str = f"{memory_context_str}\n\n{gift_memory_str}"
                else:
                    memory_context_str = gift_memory_str
            
            # 6. 构建System Prompt
            
            # 6.0 获取临时升阶和NSFW解锁
            stage_boost = 0
            stage_boost_info = None
            nsfw_override = False
            try:
                from app.services.effect_service import effect_service as _effect_svc
                stage_boost = await _effect_svc.get_stage_boost(
                    request.user_id, request.character_id
                )
                # 检查是否有角色特定的NSFW解锁
                nsfw_override = await _effect_svc.get_nsfw_override(
                    request.user_id, request.character_id
                )
                
                if stage_boost > 0:
                    # 计算原始阶段和升阶后阶段用于UI展示
                    from app.services.intimacy_constants import (
                        get_stage, STAGE_ORDER, STAGE_NAMES_CN
                    )
                    intimacy = int(user_state.intimacy_x)
                    original_stage = get_stage(intimacy)
                    stage_index = STAGE_ORDER.index(original_stage) if original_stage in STAGE_ORDER else 0
                    boosted_index = min(stage_index + stage_boost, len(STAGE_ORDER) - 1)
                    boosted_stage = STAGE_ORDER[boosted_index]
                    
                    stage_boost_info = {
                        "active": True,
                        "boost_amount": stage_boost,
                        "original_stage": original_stage.name,
                        "original_stage_cn": STAGE_NAMES_CN.get(original_stage, "未知"),
                        "boosted_stage": boosted_stage.name,
                        "boosted_stage_cn": STAGE_NAMES_CN.get(boosted_stage, "未知"),
                        "hint": f"🍷 临时升阶中：{STAGE_NAMES_CN.get(original_stage)} → {STAGE_NAMES_CN.get(boosted_stage)}",
                        "nsfw_override": nsfw_override,
                    }
                    logger.info(f"🎭 Stage boost active: {stage_boost_info['hint']}, nsfw_override={nsfw_override}")
                elif nsfw_override:
                    logger.info(f"🍷 NSFW override active (no stage boost)")
            except Exception as e:
                logger.warning(f"Failed to get stage boost: {e}")
            
            system_prompt = prompt_builder_v4.build_system_prompt(
                user_state=user_state,
                character_id=request.character_id,
                precompute_result=precompute_result,
                context_messages=context_messages,
                memory_context=memory_context_str,
                user_interests=user_interests,
                stage_boost=stage_boost,
                nsfw_override=nsfw_override,
            )
            
            # 6.1 注入状态效果 (Tier 2 礼物 prompt modifier)
            effect_modifier = None
            try:
                from app.services.effect_service import effect_service
                effect_modifier = await effect_service.get_combined_prompt_modifier(
                    request.user_id, request.character_id
                )
                if effect_modifier:
                    system_prompt = f"{system_prompt}\n\n{effect_modifier}"
                    logger.info(f"🍷 Active effects injected into V4 prompt")
            except Exception as e:
                logger.warning(f"Failed to load effects for V4: {e}")
            
            # 6.2 注入约会状态
            date_info = None
            try:
                from app.services.date_service import date_service
                date_info = await date_service.get_active_date(
                    request.user_id, request.character_id
                )
                if date_info:
                    date_prompt = date_info.get("prompt_modifier") or \
                        f"[约会模式] 你们正在 {date_info.get('scenario_name', '约会')} 中"
                    system_prompt = f"{system_prompt}\n\n{date_prompt}"
                    logger.info(f"💕 Date mode injected: {date_info.get('scenario_name')}")
            except Exception as e:
                logger.warning(f"Failed to load date status for V4: {e}")
            
            # 6.5 日志：打印完整 System Prompt（方便调试）
            logger.info(f"📝 === FULL SYSTEM PROMPT ({len(system_prompt)} chars) ===\n{system_prompt}\n=== END SYSTEM PROMPT ===")
            
            # 7. 单次LLM调用（包含对话历史）
            async with perf.track_async("llm"):
                llm_response = await self._call_llm(system_prompt, request.message, context_messages)
            
            # 7.5 日志：LLM 原始返回
            logger.info(f"🤖 LLM raw response: {llm_response['content'][:500]}")
            
            # 8. JSON解析
            with perf.track("parse"):
                parsed_response = json_parser.parse_llm_response(llm_response["content"])
            
            # 9. 存储助手回复（用户消息已在步骤5.5存储）
            async with perf.track_async("db_save_asst"):
                assistant_msg = await chat_repo.add_message(
                    session_id=request.session_id,
                    role="assistant",
                    content=parsed_response.reply,
                    tokens_used=llm_response["tokens_used"]
                )
                message_id = assistant_msg["message_id"]
            
            # 9.5 获取瓶颈锁状态
            bottleneck_info = None
            try:
                from app.services.intimacy_service import intimacy_service as _int_svc
                bottleneck_info = await _int_svc.get_bottleneck_lock_status(
                    request.user_id, request.character_id
                )
            except Exception as e:
                logger.warning(f"Failed to get bottleneck status: {e}")
            
            # 10. 异步后置更新（包括记忆提取 + 状态效果递减）
            asyncio.create_task(
                self._async_post_update(
                    user_state, precompute_result, parsed_response,
                    user_message=request.message,
                    assistant_reply=parsed_response.reply,
                    context_messages=context_messages,
                )
            )
            
            # 10.5 递减状态效果计数
            if effect_modifier:
                try:
                    expired = await effect_service.decrement_effects(
                        request.user_id, request.character_id
                    )
                    if expired:
                        for e in expired:
                            logger.info(f"🍷 Effect expired: {e['effect_type']}")
                except Exception as e:
                    logger.warning(f"Failed to decrement effects: {e}")
            
            # 11. 构建响应
            # 性能日志
            perf.log_summary("chat")
            elapsed = perf.total_elapsed
            logger.info(f"✅ V4 Pipeline completed in {elapsed:.2f}s, "
                       f"tokens: {llm_response['tokens_used']}")
            
            return ChatResponseV4(
                message_id=message_id,
                content=parsed_response.reply,
                tokens_used=llm_response["tokens_used"],
                character_name=self._get_character_name(request.character_id),
                emotion_delta=parsed_response.emotion_delta,
                intent=parsed_response.intent,
                is_nsfw_blocked=parsed_response.is_nsfw_blocked,
                thought=parsed_response.thought,
                parse_success=parsed_response.parse_success,
                parse_error=parsed_response.parse_error,
                extra_data={
                    "precompute": {
                        "intent": precompute_result.intent,
                        "difficulty": precompute_result.difficulty_rating,
                        "sentiment": precompute_result.sentiment_score,
                        "is_nsfw": precompute_result.is_nsfw
                    },
                    "user_state": {
                        "intimacy_level": user_state.intimacy_level,
                        "intimacy": int(user_state.intimacy_x),
                        "emotion": user_state.emotion,
                        "events": user_state.events
                    },
                    "v4_metrics": {
                        "elapsed_seconds": round(elapsed, 2),
                        "parse_success": parsed_response.parse_success,
                        "perf": {k: round(v, 3) for k, v in perf.stages.items()}
                    },
                    "bottleneck": bottleneck_info if bottleneck_info else {},
                    "stage_boost": stage_boost_info if stage_boost_info else None,
                }
            )
            
        except Exception as e:
            logger.error(f"❌ V4 Pipeline error: {e}", exc_info=True)
            return self._create_error_response(str(e))
    
    async def _load_user_state(self, user_id: str, character_id: str) -> UserStateV4:
        """加载用户状态"""
        
        try:
            # 从intimacy_service获取等级
            from app.services.intimacy_service import intimacy_service
            intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
            
            # 从emotion_engine获取情绪
            from app.services.emotion_engine_v2 import emotion_engine
            emotion_score = await emotion_engine.get_score(user_id, character_id)
            
            # 获取事件列表
            events = []
            try:
                from app.core.database import get_db
                from sqlalchemy import select
                from app.models.database.intimacy_models import UserIntimacy
                
                async with get_db() as db:
                    result = await db.execute(
                        select(UserIntimacy).where(
                            UserIntimacy.user_id == user_id,
                            UserIntimacy.character_id == character_id
                        )
                    )
                    intimacy_record = result.scalar_one_or_none()
                    if intimacy_record and intimacy_record.events:
                        events = intimacy_record.events if isinstance(intimacy_record.events, list) else []
            except Exception as e:
                logger.warning(f"Failed to load events: {e}")
            
            level = intimacy_data.get("current_level", 1)
            emotion = int(emotion_score)
            
            return UserStateV4(
                user_id=user_id,
                character_id=character_id,
                intimacy_level=level,
                emotion=emotion,
                events=events
            )
            
        except Exception as e:
            logger.warning(f"Failed to load user state: {e}")
            return UserStateV4(user_id=user_id, character_id=character_id)
    
    async def _load_user_interests(self, user_id: str) -> List[str]:
        """加载用户兴趣标签（display_name列表，最多5个）"""
        try:
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.interest_models import user_interests as ui_table
            from app.api.v1.interests import PREDEFINED_INTERESTS
            
            async with get_db() as db:
                result = await db.execute(
                    select(ui_table.c.interest_id).where(
                        ui_table.c.user_id == user_id
                    )
                )
                interest_ids = [row[0] for row in result.fetchall()]
            
            if not interest_ids:
                return []
            
            # Map IDs to display names (strip emoji prefix for cleaner prompt)
            id_to_name = {i["id"]: i["display_name"] for i in PREDEFINED_INTERESTS}
            names = [id_to_name[iid] for iid in interest_ids[:5] if iid in id_to_name]
            
            if names:
                logger.info(f"📌 User interests loaded: {names}")
            
            return names
            
        except Exception as e:
            logger.warning(f"Failed to load user interests: {e}")
            return []
    
    async def _load_memory_context(
        self, user_id: str, character_id: str,
        current_message: str, context_messages: List[Dict[str, str]],
        intimacy_level: int
    ) -> str:
        """加载记忆上下文并生成 prompt 文本"""
        try:
            from app.services.memory_integration_service import (
                get_memory_context_for_chat,
                generate_memory_prompt,
            )
            
            memory_ctx = await get_memory_context_for_chat(
                user_id=user_id,
                character_id=character_id,
                current_message=current_message,
                working_memory=context_messages or [],
            )
            
            if memory_ctx:
                memory_text = generate_memory_prompt(
                    memory_context=memory_ctx,
                    intimacy_level=intimacy_level,
                    current_query=current_message,
                )
                if memory_text and memory_text.strip():
                    logger.info(f"🧠 Memory context loaded ({len(memory_text)} chars)")
                    return memory_text
            
            logger.info("🧠 No memory context available")
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")
            return ""
    
    async def _load_gift_memory(self, user_id: str, character_id: str) -> str:
        """加载礼物记忆上下文"""
        try:
            from app.services.gift_service import gift_service
            
            gift_summary = await gift_service.get_gift_summary(user_id, character_id)
            if gift_summary["total_gifts"] == 0:
                return ""
            
            gift_lines = ["### 礼物记忆"]
            gift_lines.append(
                f"用户送过你 {gift_summary['total_gifts']} 次礼物，"
                f"总价值 {gift_summary['total_spent']} 月石。"
            )
            
            if gift_summary["top_gifts"]:
                top = gift_summary["top_gifts"][:3]
                gifts_str = "、".join([
                    f"{g.get('icon', '🎁')} {g.get('name_cn') or g.get('name')}({g['count']}次)"
                    for g in top
                ])
                gift_lines.append(f"常收到：{gifts_str}")
            
            result = "\n".join(gift_lines)
            logger.info(f"🎁 Gift memory loaded: {gift_summary['total_gifts']} gifts")
            return result
            
        except Exception as e:
            logger.warning(f"Failed to load gift memory: {e}")
            return ""
    
    async def _get_context_messages(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话上下文"""
        
        try:
            messages = await chat_repo.get_recent_messages(session_id, count=10)
            
            context = []
            for msg in messages:
                # 跳过系统消息
                if msg["role"] == "system":
                    continue
                
                context.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to load context: {e}")
            return []
    
    async def _call_llm(
        self, system_prompt: str, user_message: str,
        context_messages: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """调用LLM（包含对话历史）"""
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # 注入对话历史（最近10轮）
        if context_messages:
            for msg in context_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        
        # 当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"📨 LLM call: {len(messages)} messages "
                    f"(1 system + {len(messages)-2} history + 1 current)")
        
        try:
            response = await self.grok_service.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            return {
                "content": response["choices"][0]["message"]["content"],
                "tokens_used": response.get("usage", {}).get("total_tokens", 0)
            }
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    async def _store_messages(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_reply: str,
        tokens_used: int
    ) -> str:
        """存储对话消息 (legacy, 现在主流程在 process_message 中分步存储)"""
        
        # 存储用户消息
        await chat_repo.add_message(
            session_id=session_id,
            role="user",
            content=user_message,
            tokens_used=0
        )
        
        # 存储助手回复
        assistant_msg = await chat_repo.add_message(
            session_id=session_id,
            role="assistant", 
            content=assistant_reply,
            tokens_used=tokens_used
        )
        
        return assistant_msg["message_id"]
    
    async def _async_post_update(
        self,
        user_state: UserStateV4,
        precompute_result: PrecomputeResult,
        parsed_response: ParsedResponse,
        user_message: str = "",
        assistant_reply: str = "",
        context_messages: List[Dict[str, str]] = None,
    ) -> None:
        """异步后置更新（情绪、XP、事件、记忆提取）"""
        
        try:
            # 1. 更新情绪（带阶段瓶颈锁）
            delta = parsed_response.emotion_delta
            if delta != 0:
                # 阶段瓶颈 × 角色性格系数（后端兜底，防止 AI 无视 prompt 指令）
                if delta > 0:
                    from app.services.intimacy_constants import get_stage, RelationshipStage
                    from app.api.v1.characters import get_character_by_id
                    
                    intimacy = int(getattr(user_state, 'intimacy_x', 0))
                    stage = get_stage(intimacy)
                    
                    # S3/S4 不限制
                    stage_base_caps = {
                        RelationshipStage.S0_STRANGER: 20,
                        RelationshipStage.S1_FRIEND: 20,
                        RelationshipStage.S2_CRUSH: 25,
                    }
                    base_cap = stage_base_caps.get(stage)
                    
                    if base_cap:
                        # 角色 sensitivity 系数：sensitivity 越高，情绪波动越大
                        sensitivity = 5  # 默认中等
                        char_data = get_character_by_id(user_state.character_id)
                        if char_data and char_data.get("personality"):
                            sensitivity = char_data["personality"].get("sensitivity", 5)
                        
                        # 公式：base_cap × (0.6 + sensitivity × 0.1)
                        # sensitivity 3 → ×0.9, sensitivity 5 → ×1.1, sensitivity 8 → ×1.4
                        modifier = 0.6 + sensitivity * 0.1
                        cap = int(base_cap * modifier)
                        
                        if delta > cap:
                            logger.info(f"🔒 Stage cap: {stage.name} × sensitivity={sensitivity} "
                                       f"→ cap={cap}, delta {delta:+d} → +{cap}")
                            delta = cap
                
                await self._update_emotion(
                    user_state.user_id,
                    user_state.character_id,
                    delta
                )
            
            # 2. 奖励XP
            await self._award_xp(
                user_state.user_id,
                user_state.character_id,
                precompute_result.intent
            )
            
            # 3. 检查事件触发
            await self._check_event_triggers(
                user_state,
                precompute_result,
                parsed_response
            )
            
            # 4. 记忆提取（从对话中提取用户信息和重要事件）
            if user_message:
                await self._extract_memory(
                    user_state.user_id,
                    user_state.character_id,
                    user_message,
                    assistant_reply,
                    context_messages or [],
                )

            # 5. 用户记忆自动提取（LLM 分类提取，写入 user_memories 表）
            if user_message:
                await self._extract_user_memory(
                    user_state.user_id,
                    user_state.character_id,
                    user_message,
                    assistant_reply,
                )

            logger.info(f"✅ Post-update completed for user {user_state.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Post-update failed: {e}", exc_info=True)
    
    async def _extract_memory(
        self, user_id: str, character_id: str,
        user_message: str, assistant_reply: str,
        context_messages: List[Dict[str, str]]
    ) -> None:
        """从对话中提取记忆（语义+情节）"""
        try:
            from app.services.memory_integration_service import process_conversation_for_memory
            
            result = await process_conversation_for_memory(
                user_id=user_id,
                character_id=character_id,
                user_message=user_message,
                assistant_response=assistant_reply,
                context=context_messages,
            )
            
            if result.get("semantic_updated") or result.get("episodic_created"):
                logger.info(f"🧠 Memory extracted: {result.get('updates', {})}")
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")
    
    async def _extract_user_memory(
        self,
        user_id: str,
        character_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """LLM 自动提取分类记忆（写入 user_memories 表，供前端展示和管理）"""
        try:
            from app.services.subscription_service import subscription_service
            from app.services.user_memory_service import extract_memories_from_chat

            tier = await subscription_service.get_effective_tier(user_id)
            await extract_memories_from_chat(
                user_id=user_id,
                character_id=character_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
                tier=tier,
            )
        except Exception as e:
            logger.warning(f"User memory extraction failed: {e}")

    # 近期 emotion delta 历史（用于递减防刷）
    _recent_deltas: dict = {}  # key -> list of (timestamp, delta)
    
    def _apply_diminishing_returns(self, user_id: str, character_id: str, delta: int) -> int:
        """
        递减效应：连续同方向情绪变化会衰减
        - 连续正向：第1次100%, 第2次70%, 第3次40%, 第4次+20%
        - 连续负向：不衰减（惩罚不打折）
        - 5分钟内的变化算"连续"
        """
        import time
        key = f"{user_id}:{character_id}"
        now = time.time()
        
        # 初始化或清理过期记录
        if key not in self._recent_deltas:
            self._recent_deltas[key] = []
        
        # 只保留5分钟内的记录
        self._recent_deltas[key] = [
            (ts, d) for ts, d in self._recent_deltas[key] 
            if now - ts < 300
        ]
        
        # 负向不衰减
        if delta <= 0:
            self._recent_deltas[key].append((now, delta))
            return delta
        
        # 计算连续正向次数
        consecutive_positive = 0
        for _, d in reversed(self._recent_deltas[key]):
            if d > 0:
                consecutive_positive += 1
            else:
                break
        
        # 递减系数
        decay_factors = [1.0, 0.7, 0.4, 0.2, 0.1]
        factor = decay_factors[min(consecutive_positive, len(decay_factors) - 1)]
        
        adjusted = max(1, int(delta * factor))  # 至少+1
        
        if factor < 1.0:
            logger.info(f"📉 Diminishing returns: {delta:+d} × {factor} = {adjusted:+d} "
                       f"(consecutive positive: {consecutive_positive})")
        
        self._recent_deltas[key].append((now, adjusted))
        return adjusted
    
    async def _update_emotion(self, user_id: str, character_id: str, delta: int) -> None:
        """更新情绪分数（带递减防刷 + 边界软着陆）"""
        
        try:
            from app.services.emotion_engine_v2 import emotion_engine
            
            # 获取当前分数，做边界软着陆
            current = await emotion_engine.get_score(user_id, character_id)
            original_delta = delta
            
            # 边界软着陆：越接近 ±100，delta 越小
            if delta > 0 and current > 80:
                # 剩余空间比例：current=80 → 100%, current=100 → 0%
                remaining_ratio = max(0.05, (100 - current) / 20)
                delta = max(1, int(delta * remaining_ratio))
            elif delta < 0 and current < -80:
                remaining_ratio = max(0.05, (current + 100) / 20)
                delta = min(-1, int(delta * remaining_ratio))
            
            if delta != original_delta:
                logger.info(f"📊 Boundary softening: score={current}, "
                           f"delta {original_delta:+d} → {delta:+d}")
            
            # 应用连续递减效应
            adjusted_delta = self._apply_diminishing_returns(user_id, character_id, delta)
            
            await emotion_engine.update_score(
                user_id, character_id, adjusted_delta, 
                reason="v4_pipeline_update"
            )
            if adjusted_delta != original_delta:
                logger.info(f"📊 Emotion updated: {adjusted_delta:+d} (AI wanted {original_delta:+d}, score was {current})")
            else:
                logger.info(f"📊 Emotion updated: {delta:+d} (score: {current} → ~{current+delta})")
        except Exception as e:
            logger.warning(f"Emotion update failed: {e}")
    
    async def _award_xp(self, user_id: str, character_id: str, intent: str) -> None:
        """奖励XP"""
        
        try:
            from app.services.intimacy_service import intimacy_service
            
            # Check for XP multiplier from active effects
            xp_multiplier = 1.0
            try:
                from app.services.effect_service import effect_service
                xp_multiplier = await effect_service.get_xp_multiplier(user_id, character_id)
            except Exception:
                pass
            
            # 基础消息XP
            result = await intimacy_service.award_xp(user_id, character_id, "message")
            if result.get("success"):
                base_xp = result.get('xp_awarded', 0)
                # Apply multiplier for bonus XP (beyond base)
                if xp_multiplier > 1.0 and base_xp > 0:
                    bonus = int(base_xp * (xp_multiplier - 1))
                    if bonus > 0:
                        await intimacy_service.award_xp_direct(
                            user_id, character_id, bonus, reason="xp_boost_effect"
                        )
                        logger.info(f"📊 XP boost: base={base_xp}, bonus={bonus} (×{xp_multiplier})")
                else:
                    logger.info(f"📊 XP awarded: +{base_xp}")
            
            # 特殊意图额外奖励
            bonus_intents = {
                "LOVE_CONFESSION": "emotional",
                "COMPLIMENT": "emotional",
                "EXPRESS_SADNESS": "emotional",
                "APOLOGY": "emotional"
            }
            
            if intent in bonus_intents:
                bonus_type = bonus_intents[intent]
                bonus_result = await intimacy_service.award_xp(user_id, character_id, bonus_type)
                if bonus_result.get("success"):
                    logger.info(f"📊 Bonus XP for {intent}: +{bonus_result.get('xp_awarded', 0)}")
                    
        except Exception as e:
            logger.warning(f"XP award failed: {e}")
    
    async def _check_event_triggers(
        self,
        user_state: UserStateV4,
        precompute_result: PrecomputeResult,
        parsed_response: ParsedResponse
    ) -> None:
        """检查事件触发 (简化版)"""
        
        try:
            intent = precompute_result.intent
            events = user_state.events
            
            new_event = None
            
            # 简化的事件触发逻辑
            if intent == "GIFT_SEND" and "first_gift" not in events:
                new_event = "first_gift"
            elif intent == "LOVE_CONFESSION" and "first_confession" not in events:
                new_event = "first_confession"
            elif intent == "INVITATION" and "first_date" not in events:
                new_event = "first_date"
            elif intent == "REQUEST_NSFW" and not parsed_response.is_nsfw_blocked and "first_nsfw" not in events:
                new_event = "first_nsfw"
            
            if new_event:
                # 保存新事件
                from app.core.database import get_db
                from sqlalchemy import update
                from app.models.database.intimacy_models import UserIntimacy
                
                events.append(new_event)
                
                async with get_db() as db:
                    await db.execute(
                        update(UserIntimacy)
                        .where(
                            UserIntimacy.user_id == user_state.user_id,
                            UserIntimacy.character_id == user_state.character_id
                        )
                        .values(events=events)
                    )
                    await db.commit()
                
                logger.info(f"🎉 New event triggered: {new_event}")
                
        except Exception as e:
            logger.warning(f"Event check failed: {e}")
    
    def _get_character_name(self, character_id: str) -> str:
        """获取角色名称"""
        
        try:
            from app.api.v1.characters import get_character_by_id
            char_data = get_character_by_id(character_id)
            return char_data.get("name", "AI Companion") if char_data else "AI Companion"
        except:
            return "AI Companion"
    
    def _create_blocked_response(self, reason: str) -> ChatResponseV4:
        """创建拦截响应"""
        
        return ChatResponseV4(
            message_id="blocked",
            content=f"[系统提示] {reason}",
            tokens_used=0,
            character_name="系统",
            extra_data={"blocked": True, "reason": reason}
        )
    
    def _create_cold_war_response(
        self, 
        user_state: UserStateV4, 
        precompute_result: PrecomputeResult
    ) -> ChatResponseV4:
        """创建冷战状态响应"""
        
        if precompute_result.intent == "APOLOGY":
            reply = "（抬头瞥了一眼，然后又低下头）......"
        else:
            reply = "（沉默。继续看着手机，没有抬头）"
        
        return ChatResponseV4(
            message_id="cold_war",
            content=reply,
            tokens_used=0,
            character_name=self._get_character_name(user_state.character_id),
            emotion_delta=0,
            intent="IGNORE",
            extra_data={"cold_war": True, "emotion": user_state.emotion}
        )
    
    def _create_error_response(self, error: str) -> ChatResponseV4:
        """创建错误响应"""
        
        return ChatResponseV4(
            message_id="error",
            content="抱歉，我刚才有点走神了。能再说一遍吗？",
            tokens_used=0,
            character_name="AI Companion",
            parse_success=False,
            parse_error=error,
            extra_data={"error": True, "error_message": error}
        )


# 单例
chat_pipeline_v4 = ChatPipelineV4()