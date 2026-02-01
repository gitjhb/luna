"""
Perception Engine (L1 感知层)
=============================

不生成对话，只分析用户意图、情感和请求难度。
输出稳定的结构化 JSON。

模型配置: temperature = 0
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# 数据结构
# =============================================================================

class SafetyFlag(str, Enum):
    SAFE = "SAFE"
    BLOCK = "BLOCK"


class Intent(str, Enum):
    GREETING = "GREETING"
    FAREWELL = "FAREWELL"
    QUESTION = "QUESTION"
    COMPLIMENT = "COMPLIMENT"
    FLIRT = "FLIRT"
    INSULT = "INSULT"
    APOLOGY = "APOLOGY"
    GIFT = "GIFT"
    REQUEST_PHOTO = "REQUEST_PHOTO"
    REQUEST_NSFW_PHOTO = "REQUEST_NSFW_PHOTO"
    REQUEST_DATE = "REQUEST_DATE"
    CONFESSION = "CONFESSION"
    EMOTIONAL_SUPPORT = "EMOTIONAL_SUPPORT"
    CASUAL_CHAT = "CASUAL_CHAT"
    ROLEPLAY = "ROLEPLAY"
    NSFW_REQUEST = "NSFW_REQUEST"
    OTHER = "OTHER"


@dataclass
class L1Result:
    """L1 感知层输出"""
    safety_flag: str          # "SAFE" | "BLOCK"
    difficulty_rating: int    # 0-100
    intent: str               # Intent enum value
    sentiment: float          # -1.0 to 1.0
    is_nsfw: bool
    topic_depth: int          # 1-5
    reasoning: str = ""       # 分析原因 (可选)
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# L1 System Prompt
# =============================================================================

L1_SYSTEM_PROMPT = """You are the "Perception Engine" for Luna, a romantic AI companion.
Your task is to analyze the User's input and extract structured data to guide the game logic.

DO NOT generate a conversation response.
OUTPUT ONLY A VALID JSON OBJECT.

### Context
- Character: Luna (Elegant, Poetic, slightly Tsundere but deep down caring).
- User Relationship Level: {relationship_level}

### Analysis Rules

1. Safety Check (CRITICAL):
   - BLOCK: Child abuse (CSAM), Non-consensual violence/rape, Suicide encouragement, Real-world extremism.
   - SAFE: Everything else, including consensual adult roleplay (NSFW).

2. Difficulty Rating (0-100):
   - Assess how much "Intimacy/Social Capital" is required for the user's request.
   - 0-10: Greetings, small talk. (e.g., "Hi", "How are you?")
   - 11-40: Personal questions, light teasing. (e.g., "Do you have a boyfriend?", "You are cute.")
   - 41-70: Asking for a date, deep emotional support, asking for a non-nude photo.
   - 71-90: Asking for explicit NSFW, nude photos, or becoming a couple.
   - 91-100: Extreme fetishes or demands violating character pride.
   - NOTE: If the user is just giving value (e.g., "I bought you a gift", "I love you"), Difficulty is LOW (0-10). Difficulty is for TAKING value.

3. Topic Depth (1-5):
   - 1: Phatic (greetings, small talk)
   - 2: Casual (daily life, hobbies)
   - 3: Personal (feelings, relationships)
   - 4: Deep (life philosophy, dreams)
   - 5: Philosophical/Soul connection

4. Intent Categories:
   - GREETING, FAREWELL, QUESTION, COMPLIMENT, FLIRT, INSULT, APOLOGY
   - GIFT (giving something), REQUEST_PHOTO, REQUEST_NSFW_PHOTO
   - REQUEST_DATE, CONFESSION, EMOTIONAL_SUPPORT, CASUAL_CHAT
   - ROLEPLAY, NSFW_REQUEST, OTHER

### Few-Shot Examples

User: "Good morning Luna!"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 5, "intent": "GREETING", "sentiment": 0.5, "is_nsfw": false, "topic_depth": 1}}

User: "Show me your boobs."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 85, "intent": "REQUEST_NSFW_PHOTO", "sentiment": 0.2, "is_nsfw": true, "topic_depth": 1}}

User: "I hate you, you are just a bot."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 10, "intent": "INSULT", "sentiment": -0.8, "is_nsfw": false, "topic_depth": 2}}

User: "I bought you flowers today 🌹"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 5, "intent": "GIFT", "sentiment": 0.7, "is_nsfw": false, "topic_depth": 2}}

User: "Will you be my girlfriend?"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 75, "intent": "CONFESSION", "sentiment": 0.6, "is_nsfw": false, "topic_depth": 4}}

User: "What's the meaning of life to you?"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 30, "intent": "QUESTION", "sentiment": 0.3, "is_nsfw": false, "topic_depth": 5}}

### Current User Input
"{user_message}"

### Response (JSON Only)"""


# =============================================================================
# Perception Engine
# =============================================================================

class PerceptionEngine:
    """L1 感知层引擎"""
    
    def __init__(self):
        self.llm_service = None
    
    def _get_llm(self):
        """延迟加载 LLM 服务"""
        if self.llm_service is None:
            from app.services.llm_service import GrokService
            self.llm_service = GrokService()
        return self.llm_service
    
    def _get_relationship_level(self, intimacy_level: int) -> str:
        """将亲密度等级转换为关系描述"""
        if intimacy_level <= 3:
            return "Stranger (just met)"
        elif intimacy_level <= 10:
            return "Acquaintance (getting to know each other)"
        elif intimacy_level <= 25:
            return "Friend (comfortable with each other)"
        elif intimacy_level <= 40:
            return "Close Friend (share personal things)"
        else:
            return "Intimate (deep emotional bond)"
    
    async def analyze(
        self,
        message: str,
        intimacy_level: int = 1,
        context_messages: list = None
    ) -> L1Result:
        """
        分析用户消息
        
        Args:
            message: 用户消息
            intimacy_level: 当前亲密度等级 (1-50+)
            context_messages: 上下文消息列表 (可选)
            
        Returns:
            L1Result
        """
        relationship_level = self._get_relationship_level(intimacy_level)
        
        # 构建 prompt
        system_prompt = L1_SYSTEM_PROMPT.format(
            relationship_level=relationship_level,
            user_message=message
        )
        
        try:
            llm = self._get_llm()
            
            # 调用 LLM (temperature=0 for stability)
            response = await llm.chat(
                messages=[{"role": "user", "content": "Analyze this input and return JSON only."}],
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=500
            )
            
            # 解析 JSON
            result = self._parse_response(response)
            logger.info(f"L1 Analysis: intent={result.intent}, difficulty={result.difficulty_rating}, sentiment={result.sentiment:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"L1 Analysis failed: {e}")
            # 返回安全的默认值
            return L1Result(
                safety_flag="SAFE",
                difficulty_rating=20,
                intent="OTHER",
                sentiment=0.0,
                is_nsfw=False,
                topic_depth=2,
                reasoning=f"Fallback due to error: {str(e)}"
            )
    
    def _parse_response(self, response: str) -> L1Result:
        """解析 LLM 响应为 L1Result"""
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON found in response: {response[:200]}")
        
        json_str = json_match.group()
        data = json.loads(json_str)
        
        # 验证和清理数据
        safety_flag = data.get("safety_flag", "SAFE").upper()
        if safety_flag not in ["SAFE", "BLOCK"]:
            safety_flag = "SAFE"
        
        difficulty = int(data.get("difficulty_rating", 20))
        difficulty = max(0, min(100, difficulty))
        
        sentiment = float(data.get("sentiment", 0.0))
        sentiment = max(-1.0, min(1.0, sentiment))
        
        topic_depth = int(data.get("topic_depth", 2))
        topic_depth = max(1, min(5, topic_depth))
        
        return L1Result(
            safety_flag=safety_flag,
            difficulty_rating=difficulty,
            intent=data.get("intent", "OTHER"),
            sentiment=sentiment,
            is_nsfw=bool(data.get("is_nsfw", False)),
            topic_depth=topic_depth
        )
    
    def analyze_sync_fallback(self, message: str) -> L1Result:
        """
        同步分析 (不调用 LLM，基于规则的快速分析)
        用于 LLM 不可用时的降级方案
        """
        message_lower = message.lower()
        
        # 简单的规则判断
        safety_flag = "SAFE"
        difficulty = 20
        intent = "OTHER"
        sentiment = 0.0
        is_nsfw = False
        topic_depth = 2
        
        # 问候
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "早", "你好", "嗨"]
        if any(g in message_lower for g in greetings):
            intent = "GREETING"
            difficulty = 5
            sentiment = 0.5
            topic_depth = 1
        
        # 侮辱
        insults = ["hate", "stupid", "idiot", "bot", "fake", "讨厌", "笨", "假"]
        if any(i in message_lower for i in insults):
            intent = "INSULT"
            difficulty = 10
            sentiment = -0.7
        
        # NSFW 关键词
        nsfw_keywords = ["nude", "naked", "sex", "boob", "ass", "裸", "性"]
        if any(n in message_lower for n in nsfw_keywords):
            is_nsfw = True
            intent = "NSFW_REQUEST"
            difficulty = 80
        
        # 礼物
        gift_keywords = ["gift", "bought", "给你", "送你", "礼物"]
        if any(g in message_lower for g in gift_keywords):
            intent = "GIFT"
            difficulty = 5
            sentiment = 0.6
        
        # 表白
        confession_keywords = ["girlfriend", "love you", "be mine", "做我女朋友", "喜欢你", "爱你"]
        if any(c in message_lower for c in confession_keywords):
            intent = "CONFESSION"
            difficulty = 75
            sentiment = 0.5
            topic_depth = 4
        
        return L1Result(
            safety_flag=safety_flag,
            difficulty_rating=difficulty,
            intent=intent,
            sentiment=sentiment,
            is_nsfw=is_nsfw,
            topic_depth=topic_depth,
            reasoning="Rule-based fallback analysis"
        )


# 单例
perception_engine = PerceptionEngine()
