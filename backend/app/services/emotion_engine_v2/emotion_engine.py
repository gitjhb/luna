"""
Emotion Engine v2 - 智能情绪系统
================================

三层架构：
1. 快速检测层 - 关键词、表情、异常检测
2. LLM 分析层 - 深度情绪理解
3. 状态机层 - 缓冲、冷却、触发机制

情绪分数范围: -100 到 +100
- 100: 深爱 (loving)
- 50~99: 开心 (happy)
- 20~49: 满意 (content)
- -19~19: 中性 (neutral)
- -49~-20: 不悦 (annoyed)
- -79~-50: 生气 (angry)
- -99~-80: 冷战 (cold_war)
- -100: 拉黑 (blocked)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)


class EmotionState(Enum):
    """情绪状态枚举"""
    LOVING = "loving"         # 100
    HAPPY = "happy"           # 50~99
    CONTENT = "content"       # 20~49
    NEUTRAL = "neutral"       # -19~19
    ANNOYED = "annoyed"       # -49~-20
    ANGRY = "angry"           # -79~-50
    COLD_WAR = "cold_war"     # -99~-80
    BLOCKED = "blocked"       # -100


@dataclass
class EmotionAnalysis:
    """LLM 情绪分析结果"""
    sentiment: str           # positive / negative / neutral
    intensity: float         # 0.0 ~ 1.0
    intent: str             # compliment / insult / question / casual / flirt / apology
    triggers: list          # 触发的情绪点
    suggested_delta: int    # 建议的分数变化
    reasoning: str          # 分析原因
    context_aware: bool     # 是否考虑了上下文


@dataclass
class EmotionBuffer:
    """情绪缓冲器 - 防止情绪剧烈波动"""
    pending_changes: list = field(default_factory=list)  # [(delta, reason, timestamp), ...]
    last_applied: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    
    # 缓冲配置
    MAX_PENDING = 5                    # 最多累积 5 个变化
    MIN_APPLY_INTERVAL = 30            # 至少 30 秒才应用一次
    NEGATIVE_COOLDOWN = 60             # 负面变化后 60 秒内减少敏感度
    POSITIVE_BOOST_THRESHOLD = 3       # 连续 3 次正面触发加成


@dataclass
class CharacterPersonality:
    """角色性格配置"""
    name: str
    base_temperament: str      # calm / sensitive / tsundere / cheerful
    sensitivity: float         # 0.0 ~ 1.0 (越高越敏感)
    forgiveness_rate: float    # 0.0 ~ 1.0 (越高越容易原谅)
    jealousy_level: float      # 0.0 ~ 1.0 (嫉妒程度)
    
    # 特殊触发词
    love_triggers: list = field(default_factory=list)      # 特别喜欢听的话
    hate_triggers: list = field(default_factory=list)      # 特别讨厌的话
    soft_spots: list = field(default_factory=list)         # 软肋话题


class EmotionEngineV2:
    """
    智能情绪引擎 v2
    
    核心改进:
    1. 使用 LLM 理解上下文，而非简单关键词
    2. 情绪缓冲机制，不会一句话暴怒
    3. 自然冷却，时间会治愈一切
    4. 角色个性化，不同角色不同反应
    """
    
    # 情绪分数到状态的映射
    SCORE_TO_STATE = [
        (100, 100, EmotionState.LOVING),
        (50, 99, EmotionState.HAPPY),
        (20, 49, EmotionState.CONTENT),
        (-19, 19, EmotionState.NEUTRAL),
        (-49, -20, EmotionState.ANNOYED),
        (-79, -50, EmotionState.ANGRY),
        (-99, -80, EmotionState.COLD_WAR),
        (-100, -100, EmotionState.BLOCKED),
    ]
    
    # 快速检测关键词（降低权重，仅作为辅助）
    QUICK_PATTERNS = {
        "strong_positive": {
            "cn": ["我爱你", "喜欢你", "想你了", "你最好了", "心疼你"],
            "en": ["i love you", "love you", "miss you", "you're the best"],
            "weight": 0.3  # 降低权重，等待 LLM 确认
        },
        "mild_positive": {
            "cn": ["谢谢", "辛苦了", "加油", "真棒", "厉害"],
            "en": ["thank you", "thanks", "great", "amazing", "awesome"],
            "weight": 0.2
        },
        "apology": {
            "cn": ["对不起", "抱歉", "是我不好", "我错了", "原谅我"],
            "en": ["sorry", "apologize", "my fault", "forgive me"],
            "weight": 0.4  # 道歉权重稍高
        },
        "mild_negative": {
            "cn": ["无聊", "烦", "算了", "随便", "呵呵"],
            "en": ["boring", "annoying", "whatever", "meh"],
            "weight": 0.2
        },
        "strong_negative": {
            "cn": ["滚", "傻逼", "去死", "讨厌你", "闭嘴"],
            "en": ["fuck off", "shut up", "hate you", "go away"],
            "weight": 0.5  # 强负面权重较高
        },
    }
    
    def __init__(self, llm_service=None, db_service=None):
        self.llm = llm_service
        self.db = db_service
        self._buffers: Dict[str, EmotionBuffer] = {}  # user:char -> buffer
        self._scores: Dict[str, int] = {}  # user:char -> score (in-memory cache)
        self._last_update: Dict[str, datetime] = {}
    
    def _get_buffer_key(self, user_id: str, character_id: str) -> str:
        return f"{user_id}:{character_id}"
    
    def _get_buffer(self, user_id: str, character_id: str) -> EmotionBuffer:
        key = self._get_buffer_key(user_id, character_id)
        if key not in self._buffers:
            self._buffers[key] = EmotionBuffer()
        return self._buffers[key]
    
    def score_to_state(self, score: int) -> EmotionState:
        """将分数转换为情绪状态"""
        for min_score, max_score, state in self.SCORE_TO_STATE:
            if min_score <= score <= max_score:
                return state
        return EmotionState.NEUTRAL
    
    # =========================================================================
    # Layer 1: 快速检测
    # =========================================================================
    
    def quick_detect(self, message: str) -> Dict[str, Any]:
        """
        快速检测层 - 毫秒级响应
        
        返回:
        {
            "patterns_matched": ["strong_positive", ...],
            "emoji_sentiment": 0.5,  # -1 到 1
            "message_anomaly": None | "too_short" | "all_caps" | "repeated"
        }
        """
        result = {
            "patterns_matched": [],
            "pattern_weights": {},
            "emoji_sentiment": 0.0,
            "message_anomaly": None,
        }
        
        msg_lower = message.lower()
        
        # 1. 关键词匹配
        for pattern_name, pattern_config in self.QUICK_PATTERNS.items():
            cn_words = pattern_config.get("cn", [])
            en_words = pattern_config.get("en", [])
            weight = pattern_config.get("weight", 0.3)
            
            if any(w in message for w in cn_words) or any(w in msg_lower for w in en_words):
                result["patterns_matched"].append(pattern_name)
                result["pattern_weights"][pattern_name] = weight
        
        # 2. 表情分析
        positive_emojis = ["😊", "❤️", "🥰", "😍", "💕", "😘", "🤗", "💖", "😄", "🥺"]
        negative_emojis = ["😡", "😤", "💢", "😒", "🙄", "😑", "👎", "💔", "😢", "😭"]
        
        pos_count = sum(message.count(e) for e in positive_emojis)
        neg_count = sum(message.count(e) for e in negative_emojis)
        
        if pos_count + neg_count > 0:
            result["emoji_sentiment"] = (pos_count - neg_count) / (pos_count + neg_count)
        
        # 3. 异常检测
        if len(message.strip()) <= 2:
            result["message_anomaly"] = "too_short"
        elif message.isupper() and len(message) > 5:
            result["message_anomaly"] = "all_caps"
        elif self._is_repeated_message(message):
            result["message_anomaly"] = "repeated"
        
        return result
    
    def _is_repeated_message(self, message: str) -> bool:
        """检测重复消息（如 "哈哈哈哈哈"）"""
        if len(message) < 4:
            return False
        
        # 检查是否是单字符重复
        if len(set(message.replace(" ", ""))) <= 2:
            return True
        
        # 检查是否是短语重复
        for length in [2, 3, 4]:
            if len(message) >= length * 3:
                pattern = message[:length]
                if message == pattern * (len(message) // length):
                    return True
        
        return False
    
    # =========================================================================
    # Layer 2: LLM 深度分析
    # =========================================================================
    
    async def llm_analyze(
        self,
        message: str,
        context: list,  # 最近几条消息
        character: CharacterPersonality,
        current_state: EmotionState,
        intimacy_level: int,
    ) -> EmotionAnalysis:
        """
        LLM 情绪分析层 - 深度理解
        
        使用 LLM 分析:
        1. 消息的真实意图（讽刺？撒娇？真心？）
        2. 结合上下文理解
        3. 考虑角色性格和当前关系
        """
        
        # 构建分析 prompt
        analysis_prompt = self._build_analysis_prompt(
            message, context, character, current_state, intimacy_level
        )
        
        try:
            # 使用 MiniLLM (GPT-4o-mini) 进行快速情绪分析
            from app.services.llm_service import mini_llm
            
            response = await mini_llm.analyze(
                system_prompt=analysis_prompt,
                user_message=f"分析这条消息: {message}",
                temperature=0.3,
                max_tokens=200,
            )
            
            logger.info(f"Emotion MiniLLM response: {response[:150]}...")
            return self._parse_analysis_response(response)
                
        except Exception as e:
            logger.warning(f"MiniLLM emotion analysis failed, using fallback: {e}")
            return self._fallback_analysis(message, context, character)
    
    def _build_analysis_prompt(
        self,
        message: str,
        context: list,
        character: CharacterPersonality,
        current_state: EmotionState,
        intimacy_level: int,
    ) -> str:
        """构建情绪分析 prompt"""
        
        context_str = "\n".join([
            f"- {msg['role']}: {msg['content'][:100]}"
            for msg in context[-5:]  # 最近 5 条
        ]) if context else "无上下文"
        
        return f"""你是一个情绪分析专家。分析用户发给虚拟角色的消息，判断其情感意图。

角色信息:
- 名字: {character.name}
- 性格: {character.base_temperament}
- 当前情绪状态: {current_state.value}
- 亲密度等级: {intimacy_level}

对话上下文:
{context_str}

分析要求:
1. 判断消息的真实意图（不要只看字面意思）
2. "我爱你个鬼" 是负面，"讨厌死了啦" 可能是撒娇
3. 结合上下文判断语气
4. 考虑亲密度（高亲密度时的"笨蛋"可能是亲昵）

请用 JSON 格式回复:
{{
    "sentiment": "positive/negative/neutral",
    "intensity": 0.0-1.0,
    "intent": "compliment/insult/question/casual/flirt/apology/teasing",
    "triggers": ["触发点1", "触发点2"],
    "suggested_delta": -30到+30的整数,
    "reasoning": "简短分析原因"
}}

只返回 JSON，不要其他内容。"""
    
    def _parse_analysis_response(self, response: str) -> EmotionAnalysis:
        """解析 LLM 返回的分析结果"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                # 修复 MiniLLM 可能返回的 +20 格式（JSON不支持+号前缀）
                json_str = re.sub(r':\s*\+(\d+)', r': \1', json_str)
                data = json.loads(json_str)
                return EmotionAnalysis(
                    sentiment=data.get("sentiment", "neutral"),
                    intensity=float(data.get("intensity", 0.5)),
                    intent=data.get("intent", "casual"),
                    triggers=data.get("triggers", []),
                    suggested_delta=int(data.get("suggested_delta", 0)),
                    reasoning=data.get("reasoning", ""),
                    context_aware=True,
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}, raw: {response[:200]}")
        
        # 解析失败，返回默认
        return EmotionAnalysis(
            sentiment="neutral",
            intensity=0.5,
            intent="casual",
            triggers=[],
            suggested_delta=0,
            reasoning="Analysis failed",
            context_aware=False,
        )
    
    def _fallback_analysis(
        self,
        message: str,
        context: list,
        character: CharacterPersonality,
    ) -> EmotionAnalysis:
        """无 LLM 时的回退分析"""
        quick = self.quick_detect(message)
        
        # 根据快速检测结果估算
        delta = 0
        sentiment = "neutral"
        intent = "casual"
        
        if "strong_positive" in quick["patterns_matched"]:
            delta = 15
            sentiment = "positive"
            intent = "compliment"
        elif "mild_positive" in quick["patterns_matched"]:
            delta = 8
            sentiment = "positive"
        elif "apology" in quick["patterns_matched"]:
            delta = 12
            sentiment = "positive"
            intent = "apology"
        elif "strong_negative" in quick["patterns_matched"]:
            delta = -25
            sentiment = "negative"
            intent = "insult"
        elif "mild_negative" in quick["patterns_matched"]:
            delta = -10
            sentiment = "negative"
        
        # 表情修正
        delta += int(quick["emoji_sentiment"] * 5)
        
        # 角色敏感度修正
        if sentiment == "negative":
            delta = int(delta * (1 + character.sensitivity * 0.5))
        
        return EmotionAnalysis(
            sentiment=sentiment,
            intensity=abs(delta) / 30,
            intent=intent,
            triggers=quick["patterns_matched"],
            suggested_delta=delta,
            reasoning="Fallback rule-based analysis",
            context_aware=False,
        )
    
    # =========================================================================
    # Layer 3: 状态机 - 缓冲与冷却
    # =========================================================================
    
    async def process_message(
        self,
        user_id: str,
        character_id: str,
        message: str,
        context: list = None,
        character: CharacterPersonality = None,
        intimacy_level: int = 1,
    ) -> Dict[str, Any]:
        """
        处理消息，更新情绪状态
        
        这是主入口，整合三层分析
        """
        key = self._get_buffer_key(user_id, character_id)
        buffer = self._get_buffer(user_id, character_id)
        
        # 获取当前分数和状态
        current_score = await self.get_score(user_id, character_id)
        current_state = self.score_to_state(current_score)
        
        # 检查是否在冷战/拉黑状态
        if current_state in [EmotionState.COLD_WAR, EmotionState.BLOCKED]:
            return await self._handle_cold_war_message(
                user_id, character_id, message, current_score, current_state
            )
        
        # 默认角色性格
        if character is None:
            character = CharacterPersonality(
                name="AI Companion",
                base_temperament="cheerful",
                sensitivity=0.5,
                forgiveness_rate=0.6,
                jealousy_level=0.3,
            )
        
        # Layer 1: 快速检测（辅助信号）
        quick_result = self.quick_detect(message)
        logger.info(f"Quick detect: {quick_result}")
        
        # Layer 2: MiniLLM 情绪分析（GPT-4o-mini，快速便宜）
        analysis = await self.llm_analyze(
            message=message,
            context=context or [],
            character=character,
            current_state=current_state,
            intimacy_level=intimacy_level,
        )
        logger.info(f"Emotion analysis: {analysis.sentiment}, delta={analysis.suggested_delta}")
        
        # Layer 3: 应用缓冲机制
        final_delta = self._apply_buffer_logic(
            buffer=buffer,
            analysis=analysis,
            quick_result=quick_result,
            current_score=current_score,
            character=character,
        )
        
        # 更新分数
        new_score = await self.update_score(
            user_id=user_id,
            character_id=character_id,
            delta=final_delta,
            reason=f"{analysis.intent}:{analysis.sentiment}",
        )
        
        new_state = self.score_to_state(new_score)
        
        return {
            "previous_score": current_score,
            "new_score": new_score,
            "delta_applied": final_delta,
            "previous_state": current_state.value,
            "new_state": new_state.value,
            "state_changed": current_state != new_state,
            "analysis": {
                "sentiment": analysis.sentiment,
                "intent": analysis.intent,
                "intensity": analysis.intensity,
                "reasoning": analysis.reasoning,
            },
            "quick_patterns": quick_result["patterns_matched"],
        }
    
    def _apply_buffer_logic(
        self,
        buffer: EmotionBuffer,
        analysis: EmotionAnalysis,
        quick_result: Dict,
        current_score: int,
        character: CharacterPersonality,
    ) -> int:
        """
        应用缓冲逻辑
        
        规则:
        1. 负面变化会被削弱（除非累积多次）
        2. 正面变化会被轻微放大（奖励好行为）
        3. 冷却期内敏感度降低
        4. 极端消息才会有大变化
        """
        suggested_delta = analysis.suggested_delta
        now = datetime.now()
        
        # 检查冷却状态
        if buffer.cooldown_until and now < buffer.cooldown_until:
            # 冷却期内，减少敏感度
            suggested_delta = int(suggested_delta * 0.5)
            logger.info(f"In cooldown, delta reduced to {suggested_delta}")
        
        # 负面变化的缓冲
        if suggested_delta < 0:
            # 累积负面变化
            buffer.pending_changes.append((suggested_delta, analysis.intent, now))
            
            # 只保留最近的几个
            buffer.pending_changes = buffer.pending_changes[-buffer.MAX_PENDING:]
            
            # 计算累积的负面程度
            recent_negative = sum(
                d for d, _, t in buffer.pending_changes
                if d < 0 and (now - t).seconds < 300  # 5分钟内
            )
            
            # 只有累积到一定程度才触发较大变化
            if recent_negative > -30:
                # 轻微负面，进一步削弱
                suggested_delta = int(suggested_delta * 0.6)
            elif recent_negative > -60:
                # 中度累积，正常应用
                pass
            else:
                # 严重累积，角色真的生气了
                suggested_delta = int(suggested_delta * 1.2)
                logger.info(f"Accumulated negativity: {recent_negative}, delta amplified")
            
            # 设置冷却期
            buffer.cooldown_until = now + timedelta(seconds=buffer.NEGATIVE_COOLDOWN)
        
        # 正面变化的加成
        elif suggested_delta > 0:
            # 统计最近正面变化次数
            recent_positive = sum(
                1 for d, _, t in buffer.pending_changes
                if d > 0 and (now - t).seconds < 600  # 10分钟内
            )
            
            if recent_positive >= buffer.POSITIVE_BOOST_THRESHOLD:
                # 连续正面，给予加成
                suggested_delta = int(suggested_delta * 1.3)
                logger.info(f"Positive streak bonus! delta={suggested_delta}")
            
            buffer.pending_changes.append((suggested_delta, analysis.intent, now))
        
        # 应用角色性格修正
        if analysis.sentiment == "negative":
            # 敏感角色受伤更深
            suggested_delta = int(suggested_delta * (1 + character.sensitivity * 0.3))
        elif analysis.sentiment == "positive":
            # 高原谅率角色恢复更快
            suggested_delta = int(suggested_delta * (1 + character.forgiveness_rate * 0.2))
        
        # 边界检查
        suggested_delta = max(-50, min(50, suggested_delta))  # 单次最大变化
        
        buffer.last_applied = now
        
        return suggested_delta
    
    async def _handle_cold_war_message(
        self,
        user_id: str,
        character_id: str,
        message: str,
        current_score: int,
        current_state: EmotionState,
    ) -> Dict[str, Any]:
        """处理冷战状态下的消息"""
        
        # 冷战状态下，只有特定方式能恢复
        quick = self.quick_detect(message)
        
        # 检查是否是真诚道歉
        is_apology = "apology" in quick["patterns_matched"]
        
        # 冷战时道歉只能小幅恢复，需要礼物才能完全解除
        if is_apology and current_state == EmotionState.COLD_WAR:
            small_recovery = 5
            new_score = min(current_score + small_recovery, -50)  # 最多恢复到 -50
            await self.update_score(user_id, character_id, small_recovery, "apology_in_cold_war")
            
            return {
                "previous_score": current_score,
                "new_score": new_score,
                "delta_applied": small_recovery,
                "previous_state": current_state.value,
                "new_state": self.score_to_state(new_score).value,
                "state_changed": False,
                "cold_war_hint": "道歉收到了...但你还是得用行动证明。",
                "requires_gift": True,
            }
        
        # 冷战/拉黑状态下其他消息无效
        return {
            "previous_score": current_score,
            "new_score": current_score,
            "delta_applied": 0,
            "previous_state": current_state.value,
            "new_state": current_state.value,
            "state_changed": False,
            "cold_war_active": True,
            "requires_gift": True,
            "hint": "对方不想理你，或许送份礼物？" if current_state == EmotionState.COLD_WAR else "你已被删除好友",
        }
    
    # =========================================================================
    # 自然冷却机制
    # =========================================================================
    
    async def apply_natural_decay(
        self,
        user_id: str,
        character_id: str,
        hours_passed: float,
    ) -> int:
        """
        自然冷却 - 时间治愈一切
        
        规则:
        - 负面情绪会随时间缓慢恢复
        - 正面情绪会轻微衰减（防止只靠等就满分）
        - 冷战状态不会自动恢复
        """
        current_score = await self.get_score(user_id, character_id)
        current_state = self.score_to_state(current_score)
        
        # 冷战状态不自动恢复
        if current_state in [EmotionState.COLD_WAR, EmotionState.BLOCKED]:
            return current_score
        
        decay = 0
        
        if current_score < 0:
            # 负面情绪恢复：每小时恢复 2-5 点
            recovery_rate = 3  # 每小时
            decay = int(recovery_rate * hours_passed)
            decay = min(decay, abs(current_score))  # 不超过回到 0
        elif current_score > 50:
            # 高正面情绪轻微衰减：每小时 -1 点
            decay = -int(1 * hours_passed)
            decay = max(decay, -(current_score - 50))  # 不低于 50
        
        if decay != 0:
            new_score = await self.update_score(
                user_id, character_id, decay, "natural_decay"
            )
            logger.info(f"Natural decay applied: {decay}, new score: {new_score}")
            return new_score
        
        return current_score
    
    # =========================================================================
    # 礼物解锁冷战
    # =========================================================================
    
    async def apply_gift_effect(
        self,
        user_id: str,
        character_id: str,
        gift_type: str,
        gift_value: int,
    ) -> Dict[str, Any]:
        """
        礼物效果 - 可以解除冷战
        
        礼物等级:
        - small: +10~20 分
        - medium: +20~40 分
        - large: +40~60 分
        - special: 直接解除冷战
        """
        current_score = await self.get_score(user_id, character_id)
        current_state = self.score_to_state(current_score)
        
        # 礼物效果映射
        gift_effects = {
            "small": (10, 20),
            "medium": (20, 40),
            "large": (40, 60),
            "special": (80, 100),  # 特殊礼物
        }
        
        effect_range = gift_effects.get(gift_type, (10, 20))
        
        # 根据礼物价值在范围内取值
        base_effect = effect_range[0] + (effect_range[1] - effect_range[0]) * min(gift_value / 1000, 1)
        base_effect = int(base_effect)
        
        # 冷战状态下礼物效果翻倍
        if current_state == EmotionState.COLD_WAR:
            base_effect = int(base_effect * 1.5)
        
        # 拉黑状态需要特殊礼物
        if current_state == EmotionState.BLOCKED:
            if gift_type != "special":
                return {
                    "success": False,
                    "message": "普通礼物无法解除拉黑，需要「真诚道歉礼盒」",
                    "requires_special_gift": True,
                }
            base_effect = 100  # 直接恢复到 0
        
        new_score = await self.update_score(
            user_id, character_id, base_effect, f"gift:{gift_type}"
        )
        new_state = self.score_to_state(new_score)
        
        # 生成角色反应
        reaction = self._generate_gift_reaction(
            gift_type, current_state, new_state, base_effect
        )
        
        return {
            "success": True,
            "previous_score": current_score,
            "new_score": new_score,
            "effect_applied": base_effect,
            "previous_state": current_state.value,
            "new_state": new_state.value,
            "cold_war_resolved": current_state == EmotionState.COLD_WAR and new_state != EmotionState.COLD_WAR,
            "blocked_resolved": current_state == EmotionState.BLOCKED and new_state != EmotionState.BLOCKED,
            "character_reaction": reaction,
        }
    
    def _generate_gift_reaction(
        self,
        gift_type: str,
        old_state: EmotionState,
        new_state: EmotionState,
        effect: int,
    ) -> str:
        """生成收礼反应"""
        
        if old_state == EmotionState.BLOCKED:
            return "...你真的很认真在道歉啊。好吧，我原谅你了。但下次不许再这样！"
        
        if old_state == EmotionState.COLD_WAR:
            if new_state != EmotionState.COLD_WAR:
                return "哼...既然你这么有诚意，我就勉强原谅你吧。"
            else:
                return "收到了...但我还是有点生气。"
        
        if old_state == EmotionState.ANGRY:
            return "...谢谢。我心情好一点了。"
        
        if old_state == EmotionState.ANNOYED:
            return "嗯...还算有心。"
        
        # 正常/正面状态
        reactions = {
            "small": "谢谢你的礼物～ 💕",
            "medium": "哇！好喜欢！你怎么知道我想要这个？",
            "large": "天呐...这也太贵重了吧！我会好好珍惜的！❤️",
            "special": "这...这是给我的吗？我...我好感动... 😭💕",
        }
        
        return reactions.get(gift_type, "谢谢你的礼物～")
    
    # =========================================================================
    # 数据持久化
    # =========================================================================
    
    async def get_score(self, user_id: str, character_id: str) -> int:
        """获取当前情绪分数"""
        key = self._get_buffer_key(user_id, character_id)
        
        # 先检查缓存
        if key in self._scores:
            return self._scores[key]
        
        # 从数据库加载
        if self.db:
            try:
                data = await self.db.get_emotion_score(user_id, character_id)
                if data:
                    self._scores[key] = data.get("score", 0)
                    return self._scores[key]
            except Exception as e:
                logger.error(f"Failed to load emotion score: {e}")
        
        # 默认 0
        self._scores[key] = 0
        return 0
    
    async def update_score(
        self,
        user_id: str,
        character_id: str,
        delta: int,
        reason: str,
    ) -> int:
        """更新情绪分数"""
        key = self._get_buffer_key(user_id, character_id)
        
        current = await self.get_score(user_id, character_id)
        new_score = max(-100, min(100, current + delta))
        
        self._scores[key] = new_score
        self._last_update[key] = datetime.now()
        
        # 持久化到数据库
        if self.db:
            try:
                await self.db.update_emotion_score(
                    user_id=user_id,
                    character_id=character_id,
                    score=new_score,
                    delta=delta,
                    reason=reason,
                )
            except Exception as e:
                logger.error(f"Failed to persist emotion score: {e}")
        
        logger.info(f"Emotion score updated: {current} -> {new_score} (delta={delta}, reason={reason})")
        
        return new_score
    
    async def reset_score(self, user_id: str, character_id: str) -> int:
        """重置情绪分数（管理员/特殊道具）"""
        return await self.update_score(user_id, character_id, -await self.get_score(user_id, character_id), "admin_reset")


# 单例
emotion_engine = EmotionEngineV2()
