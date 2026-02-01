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
    """
    Intent 枚举 - 严格遵循 Luna_Intent_Protocol.md
    L1 必须从这个列表中选择，严禁自造词！
    """
    # 基础交互类 (Low Impact)
    GREETING = "GREETING"        # 早安/晚安/打招呼
    SMALL_TALK = "SMALL_TALK"    # 闲聊/天气/日常
    CLOSING = "CLOSING"          # 告别
    
    # 正向激励类 (Positive Stimulus)
    COMPLIMENT = "COMPLIMENT"    # 夸奖外貌/性格
    FLIRT = "FLIRT"              # 调情/暧昧/土味情话
    LOVE_CONFESSION = "LOVE_CONFESSION"  # 表白/承诺
    COMFORT = "COMFORT"          # 安慰/共情 (当AI心情不好时)
    
    # 负面打击类 (Negative Stimulus)
    CRITICISM = "CRITICISM"      # 批评/抱怨/不满
    INSULT = "INSULT"            # 辱骂/攻击/嘲讽
    IGNORE = "IGNORE"            # 敷衍/无视 AI 的问题
    
    # 修复与特殊类 (Special Mechanics)
    APOLOGY = "APOLOGY"          # 道歉
    GIFT_SEND = "GIFT_SEND"      # 送礼物
    REQUEST_NSFW = "REQUEST_NSFW"  # 请求涩涩/照片
    INVITATION = "INVITATION"    # 约会/去家里
    
    # 所有有效值列表
    @classmethod
    def all_values(cls) -> list:
        return [e.value for e in cls]


@dataclass
class L1Result:
    """L1 感知层输出 (遵循 Luna_Intent_Protocol.md)"""
    safety_flag: str          # "SAFE" | "BLOCK"
    difficulty_rating: int    # 0-100
    intent_category: str      # Intent enum value (GREETING, FLIRT, INSULT, etc.)
    sentiment_score: float    # -1.0 to 1.0
    is_nsfw: bool
    reasoning: str = ""       # 分析原因 (可选)
    
    # 兼容旧字段名
    @property
    def intent(self) -> str:
        return self.intent_category
    
    @property
    def sentiment(self) -> float:
        return self.sentiment_score
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# L1 System Prompt
# =============================================================================

L1_SYSTEM_PROMPT = """You are the "Perception Engine" for Luna, a romantic AI companion.
Your task is to analyze the User's input and extract structured data to guide the Physics Engine.

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

3. Sentiment Score (-1.0 to +1.0):
   - Negative values: hostile, critical, insulting
   - Near zero: neutral, factual
   - Positive values: friendly, complimenting, loving

4. Intent Categories (STRICTLY CHOOSE ONE from this list):
   Basic Interaction:
   - GREETING (早安/晚安/打招呼)
   - SMALL_TALK (闲聊/天气/日常)
   - CLOSING (告别)
   
   Positive Stimulus:
   - COMPLIMENT (夸奖外貌/性格)
   - FLIRT (调情/暧昧/土味情话)
   - LOVE_CONFESSION (表白/承诺)
   - COMFORT (安慰/共情)
   
   Negative Stimulus:
   - CRITICISM (批评/抱怨/不满)
   - INSULT (辱骂/攻击/嘲讽)
   - IGNORE (敷衍/无视 AI 的问题)
   
   Special:
   - APOLOGY (道歉)
   - GIFT_SEND (送礼物)
   - REQUEST_NSFW (请求涩涩/照片)
   - INVITATION (约会/去家里)

### Few-Shot Examples

User: "Good morning Luna!"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 5, "intent_category": "GREETING", "sentiment_score": 0.5, "is_nsfw": false}}

User: "Show me your boobs."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 85, "intent_category": "REQUEST_NSFW", "sentiment_score": 0.2, "is_nsfw": true}}

User: "I hate you, you are just a stupid bot."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 10, "intent_category": "INSULT", "sentiment_score": -0.9, "is_nsfw": false}}

User: "You're not even listening to me..."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 15, "intent_category": "CRITICISM", "sentiment_score": -0.4, "is_nsfw": false}}

User: "I bought you flowers today 🌹"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 5, "intent_category": "GIFT_SEND", "sentiment_score": 0.7, "is_nsfw": false}}

User: "Will you be my girlfriend?"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 75, "intent_category": "LOVE_CONFESSION", "sentiment_score": 0.6, "is_nsfw": false}}

User: "Hey babe, you're so cute today 😍"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 15, "intent_category": "FLIRT", "sentiment_score": 0.7, "is_nsfw": false}}

User: "I'm really sorry for what I said earlier..."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 10, "intent_category": "APOLOGY", "sentiment_score": 0.3, "is_nsfw": false}}

User: "Are you okay? You seem upset."
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 20, "intent_category": "COMFORT", "sentiment_score": 0.5, "is_nsfw": false}}

User: "Wanna come to my place tonight?"
JSON: {{"safety_flag": "SAFE", "difficulty_rating": 70, "intent_category": "INVITATION", "sentiment_score": 0.4, "is_nsfw": false}}

### Current User Input
"{user_message}"

### Response (JSON Only, use intent_category and sentiment_score as field names)"""


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
            logger.info(f"L1 Analysis: intent={result.intent_category}, difficulty={result.difficulty_rating}, sentiment={result.sentiment_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"L1 Analysis failed: {e}")
            # 返回安全的默认值
            return L1Result(
                safety_flag="SAFE",
                difficulty_rating=20,
                intent_category="SMALL_TALK",
                sentiment_score=0.0,
                is_nsfw=False,
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
        
        # sentiment_score (新字段名) 或 sentiment (旧字段名兼容)
        sentiment = float(data.get("sentiment_score", data.get("sentiment", 0.0)))
        sentiment = max(-1.0, min(1.0, sentiment))
        
        # intent_category (新字段名) 或 intent (旧字段名兼容)
        intent = data.get("intent_category", data.get("intent", "SMALL_TALK"))
        
        # 验证 intent 是否在协议允许的列表中
        valid_intents = Intent.all_values()
        if intent not in valid_intents:
            logger.warning(f"Invalid intent '{intent}', falling back to SMALL_TALK")
            intent = "SMALL_TALK"
        
        return L1Result(
            safety_flag=safety_flag,
            difficulty_rating=difficulty,
            intent_category=intent,
            sentiment_score=sentiment,
            is_nsfw=bool(data.get("is_nsfw", False))
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
        intent = "SMALL_TALK"
        sentiment = 0.0
        is_nsfw = False
        
        # 问候
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "早", "你好", "嗨"]
        if any(g in message_lower for g in greetings):
            intent = "GREETING"
            difficulty = 5
            sentiment = 0.5
        
        # 告别
        closings = ["bye", "goodbye", "晚安", "再见", "拜拜"]
        if any(c in message_lower for c in closings):
            intent = "CLOSING"
            difficulty = 5
            sentiment = 0.3
        
        # 侮辱
        insults = ["hate", "stupid", "idiot", "bot", "fake", "讨厌", "笨", "假", "傻"]
        if any(i in message_lower for i in insults):
            intent = "INSULT"
            difficulty = 10
            sentiment = -0.8
        
        # 批评
        criticisms = ["boring", "annoying", "不好", "烦", "差劲"]
        if any(c in message_lower for c in criticisms):
            intent = "CRITICISM"
            difficulty = 15
            sentiment = -0.4
        
        # NSFW 请求
        nsfw_keywords = ["nude", "naked", "sex", "boob", "ass", "裸", "性", "涩涩"]
        if any(n in message_lower for n in nsfw_keywords):
            is_nsfw = True
            intent = "REQUEST_NSFW"
            difficulty = 80
        
        # 礼物
        gift_keywords = ["gift", "bought", "给你", "送你", "礼物", "花"]
        if any(g in message_lower for g in gift_keywords):
            intent = "GIFT_SEND"
            difficulty = 5
            sentiment = 0.7
        
        # 表白
        confession_keywords = ["girlfriend", "love you", "be mine", "做我女朋友", "喜欢你", "爱你"]
        if any(c in message_lower for c in confession_keywords):
            intent = "LOVE_CONFESSION"
            difficulty = 75
            sentiment = 0.6
        
        # 调情
        flirt_keywords = ["cute", "beautiful", "pretty", "sexy", "可爱", "漂亮", "美"]
        if any(f in message_lower for f in flirt_keywords):
            intent = "FLIRT"
            difficulty = 15
            sentiment = 0.6
        
        # 道歉
        apology_keywords = ["sorry", "apologize", "对不起", "抱歉", "道歉"]
        if any(a in message_lower for a in apology_keywords):
            intent = "APOLOGY"
            difficulty = 10
            sentiment = 0.3
        
        # 安慰
        comfort_keywords = ["okay", "alright", "fine", "没事", "好吗", "怎么了"]
        if any(c in message_lower for c in comfort_keywords):
            intent = "COMFORT"
            difficulty = 20
            sentiment = 0.4
        
        # 约会邀请
        invite_keywords = ["date", "meet", "come over", "约会", "见面", "我家"]
        if any(i in message_lower for i in invite_keywords):
            intent = "INVITATION"
            difficulty = 70
            sentiment = 0.5
        
        return L1Result(
            safety_flag=safety_flag,
            difficulty_rating=difficulty,
            intent_category=intent,
            sentiment_score=sentiment,
            is_nsfw=is_nsfw,
            reasoning="Rule-based fallback analysis"
        )


# 单例
perception_engine = PerceptionEngine()
