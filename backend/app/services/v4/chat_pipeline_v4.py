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
        start_time = datetime.now()
        
        try:
            # 1. 加载用户状态
            user_state = await self._load_user_state(request.user_id, request.character_id)
            logger.info(f"📊 User State: level={user_state.intimacy_level}, "
                       f"intimacy={user_state.intimacy_x:.1f}, emotion={user_state.emotion}")
            
            # 2. 前置计算 (替代L1)
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
            context_messages = await self._get_context_messages(request.session_id)
            
            # 6. 构建System Prompt
            system_prompt = prompt_builder_v4.build_system_prompt(
                user_state=user_state,
                character_id=request.character_id,
                precompute_result=precompute_result,
                context_messages=context_messages
            )
            
            # 7. 单次LLM调用
            llm_response = await self._call_llm(system_prompt, request.message)
            
            # 8. JSON解析
            parsed_response = json_parser.parse_llm_response(llm_response["content"])
            
            # 9. 存储消息
            message_id = await self._store_messages(
                request.session_id,
                request.user_id,
                request.message,
                parsed_response.reply,
                llm_response["tokens_used"]
            )
            
            # 10. 异步后置更新
            asyncio.create_task(
                self._async_post_update(user_state, precompute_result, parsed_response)
            )
            
            # 11. 构建响应
            elapsed = (datetime.now() - start_time).total_seconds()
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
                        "parse_success": parsed_response.parse_success
                    }
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
    
    async def _call_llm(self, system_prompt: str, user_message: str) -> Dict[str, Any]:
        """调用LLM"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
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
        """存储对话消息"""
        
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
        parsed_response: ParsedResponse
    ) -> None:
        """异步后置更新（情绪、XP、事件）"""
        
        try:
            # 1. 更新情绪
            if parsed_response.emotion_delta != 0:
                await self._update_emotion(
                    user_state.user_id,
                    user_state.character_id,
                    parsed_response.emotion_delta
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
            
            logger.info(f"✅ Post-update completed for user {user_state.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Post-update failed: {e}", exc_info=True)
    
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
        """更新情绪分数（带递减防刷）"""
        
        try:
            # 应用递减效应
            adjusted_delta = self._apply_diminishing_returns(user_id, character_id, delta)
            
            from app.services.emotion_engine_v2 import emotion_engine
            await emotion_engine.update_score(
                user_id, character_id, adjusted_delta, 
                reason="v4_pipeline_update"
            )
            if adjusted_delta != delta:
                logger.info(f"📊 Emotion updated: {adjusted_delta:+d} (AI wanted {delta:+d})")
            else:
                logger.info(f"📊 Emotion updated: {delta:+d}")
        except Exception as e:
            logger.warning(f"Emotion update failed: {e}")
    
    async def _award_xp(self, user_id: str, character_id: str, intent: str) -> None:
        """奖励XP"""
        
        try:
            from app.services.intimacy_service import intimacy_service
            
            # 基础消息XP
            result = await intimacy_service.award_xp(user_id, character_id, "message")
            if result.get("success"):
                logger.info(f"📊 XP awarded: +{result.get('xp_awarded', 0)}")
            
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