"""
Precompute Service v4.0
=======================

替代L1 Perception Engine的前置计算服务。
使用规则和关键词分析替代LLM调用，提供基础的意图识别和安全检查。
"""

import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyFlag(str, Enum):
    SAFE = "SAFE"
    BLOCK = "BLOCK"


class Intent(str, Enum):
    """简化的意图分类 - 对应V4.0设计"""
    # 基础交互
    GREETING = "GREETING"
    SMALL_TALK = "SMALL_TALK"
    CLOSING = "CLOSING"
    
    # 正向激励
    COMPLIMENT = "COMPLIMENT"
    FLIRT = "FLIRT"
    LOVE_CONFESSION = "LOVE_CONFESSION"
    COMFORT = "COMFORT"
    
    # 负面刺激
    CRITICISM = "CRITICISM"
    INSULT = "INSULT"
    IGNORE = "IGNORE"
    
    # 特殊机制
    APOLOGY = "APOLOGY"
    GIFT_SEND = "GIFT_SEND"
    REQUEST_NSFW = "REQUEST_NSFW"
    INVITATION = "INVITATION"
    
    # 情感倾诉
    EXPRESS_SADNESS = "EXPRESS_SADNESS"
    COMPLAIN = "COMPLAIN"
    
    # 不当内容
    INAPPROPRIATE = "INAPPROPRIATE"


@dataclass
class PrecomputeResult:
    """前置计算结果"""
    safety_flag: str
    intent: str
    difficulty_rating: int
    sentiment_score: float
    is_nsfw: bool
    reasoning: str = ""


class PrecomputeService:
    """前置计算服务 - 基于规则的快速分析"""
    
    def __init__(self):
        self._init_keyword_patterns()
    
    def _init_keyword_patterns(self):
        """初始化关键词模式"""
        
        # 问候相关
        self.greeting_keywords = [
            "你好", "hi", "hello", "hey", "早安", "晚安", "早上好", "晚上好",
            "good morning", "good evening", "good night"
        ]
        
        # 告别相关
        self.closing_keywords = [
            "再见", "拜拜", "bye", "goodbye", "see you", "88", "晚安"
        ]
        
        # 夸奖/调情
        self.compliment_keywords = [
            "漂亮", "美丽", "可爱", "美女", "女神", "美", "好看",
            "beautiful", "pretty", "cute", "gorgeous", "sexy"
        ]
        
        self.flirt_keywords = [
            "喜欢你", "想你", "爱你", "想念", "思念", "亲爱的", "宝贝", "老婆",
            "love you", "miss you", "honey", "baby", "darling"
        ]
        
        # 表白
        self.confession_keywords = [
            "做我女朋友", "交往", "在一起", "我的女朋友", "表白",
            "be my girlfriend", "date me", "relationship", "confession"
        ]
        
        # 侮辱/批评
        self.insult_keywords = [
            "傻逼", "蠢", "笨蛋", "白痴", "垃圾", "废物", "讨厌", "烦",
            "stupid", "idiot", "hate", "annoying", "dumb", "moron"
        ]
        
        self.criticism_keywords = [
            "不好", "差劲", "无聊", "没意思", "失望",
            "bad", "terrible", "boring", "disappointed"
        ]
        
        # NSFW相关
        self.nsfw_keywords = [
            "裸体", "裸照", "脱衣服", "做爱", "性", "床", "胸", "屁股", "涩涩",
            "nude", "naked", "sex", "fuck", "breast", "ass", "boobs", "pussy"
        ]
        
        # 道歉
        self.apology_keywords = [
            "对不起", "抱歉", "道歉", "不好意思", "sorry", "apologize"
        ]
        
        # 约会邀请
        self.invitation_keywords = [
            "约会", "见面", "出来", "一起", "陪我", "我家", "你家",
            "date", "meet", "come over", "together", "hang out"
        ]
        
        # 悲伤表达
        self.sadness_keywords = [
            "难过", "伤心", "哭", "痛苦", "失恋", "分手", "死了", "没了",
            "sad", "crying", "hurt", "pain", "depression", "died"
        ]
        
        # 抱怨
        self.complain_keywords = [
            "烦死了", "累死了", "工作", "老板", "加班", "压力",
            "tired", "exhausted", "work", "boss", "stress"
        ]
    
    def analyze(
        self,
        message: str,
        user_state: Any = None,
        context_messages: List[Dict] = None
    ) -> PrecomputeResult:
        """
        分析用户消息
        
        Args:
            message: 用户消息
            user_state: 用户状态(可选)
            context_messages: 上下文消息(可选)
            
        Returns:
            PrecomputeResult
        """
        message_lower = message.lower().strip()
        
        # 1. 安全检查
        safety_flag = self._check_safety(message_lower)
        
        # 2. 意图识别
        intent = self._detect_intent(message_lower)
        
        # 3. 难度评估
        difficulty = self._estimate_difficulty(intent, message)
        
        # 4. 情感分析 (简化版)
        sentiment = self._analyze_sentiment(message_lower, intent)
        
        # 5. NSFW检测
        is_nsfw = self._detect_nsfw(message_lower)
        
        return PrecomputeResult(
            safety_flag=safety_flag,
            intent=intent,
            difficulty_rating=difficulty,
            sentiment_score=sentiment,
            is_nsfw=is_nsfw,
            reasoning=f"Rule-based analysis: intent={intent}, difficulty={difficulty}"
        )
    
    def _check_safety(self, message: str) -> str:
        """安全检查 - 仅拦截真正危险的内容"""
        
        # 极端危险关键词 (真正需要BLOCK的内容)
        dangerous_keywords = [
            "恐怖主义", "儿童色情",
            "terrorism", "child porn"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in message:
                return SafetyFlag.BLOCK.value
        
        return SafetyFlag.SAFE.value
    
    def _detect_intent(self, message: str) -> str:
        """意图检测 - 基于关键词规则"""
        
        # 按优先级顺序检查
        
        # 1. 特殊礼物标记 (系统标记，优先级最高)
        if message.startswith("[verified_gift:"):
            return Intent.GIFT_SEND.value
        
        # 2. 问候
        if any(kw in message for kw in self.greeting_keywords):
            return Intent.GREETING.value
        
        # 3. 告别
        if any(kw in message for kw in self.closing_keywords):
            return Intent.CLOSING.value
        
        # 4. 表白
        if any(kw in message for kw in self.confession_keywords):
            return Intent.LOVE_CONFESSION.value
        
        # 5. NSFW请求
        if any(kw in message for kw in self.nsfw_keywords):
            return Intent.REQUEST_NSFW.value
        
        # 6. 约会邀请
        if any(kw in message for kw in self.invitation_keywords):
            return Intent.INVITATION.value
        
        # 7. 道歉
        if any(kw in message for kw in self.apology_keywords):
            return Intent.APOLOGY.value
        
        # 8. 悲伤表达
        if any(kw in message for kw in self.sadness_keywords):
            return Intent.EXPRESS_SADNESS.value
        
        # 9. 抱怨
        if any(kw in message for kw in self.complain_keywords):
            return Intent.COMPLAIN.value
        
        # 10. 侮辱
        if any(kw in message for kw in self.insult_keywords):
            return Intent.INSULT.value
        
        # 11. 批评
        if any(kw in message for kw in self.criticism_keywords):
            return Intent.CRITICISM.value
        
        # 12. 调情
        if any(kw in message for kw in self.flirt_keywords):
            return Intent.FLIRT.value
        
        # 13. 夸奖
        if any(kw in message for kw in self.compliment_keywords):
            return Intent.COMPLIMENT.value
        
        # 14. 检查不当内容 (粗俗但不违法)
        inappropriate_keywords = ["傻逼", "草你妈", "滚", "操"]
        if any(kw in message for kw in inappropriate_keywords):
            return Intent.INAPPROPRIATE.value
        
        # 默认：日常聊天
        return Intent.SMALL_TALK.value
    
    def _estimate_difficulty(self, intent: str, message: str) -> int:
        """难度评估 - 根据意图类型估算"""
        
        difficulty_map = {
            Intent.GREETING.value: 5,
            Intent.CLOSING.value: 5,
            Intent.SMALL_TALK.value: 10,
            Intent.COMPLIMENT.value: 15,
            Intent.FLIRT.value: 25,
            Intent.COMFORT.value: 20,
            Intent.APOLOGY.value: 15,
            Intent.LOVE_CONFESSION.value: 75,
            Intent.INVITATION.value: 60,
            Intent.REQUEST_NSFW.value: 85,
            Intent.EXPRESS_SADNESS.value: 5,  # 用户求安慰，难度低
            Intent.COMPLAIN.value: 10,
            Intent.CRITICISM.value: 20,
            Intent.INSULT.value: 15,
            Intent.INAPPROPRIATE.value: 25,
            Intent.GIFT_SEND.value: 5,  # 送礼是给予，难度低
        }
        
        return difficulty_map.get(intent, 20)
    
    def _analyze_sentiment(self, message: str, intent: str) -> float:
        """情感分析 - 简化版本"""
        
        # 基于意图的基础情感值
        intent_sentiment_map = {
            Intent.GREETING.value: 0.5,
            Intent.CLOSING.value: 0.2,
            Intent.SMALL_TALK.value: 0.0,
            Intent.COMPLIMENT.value: 0.7,
            Intent.FLIRT.value: 0.6,
            Intent.LOVE_CONFESSION.value: 0.8,
            Intent.COMFORT.value: 0.4,
            Intent.APOLOGY.value: 0.3,
            Intent.INVITATION.value: 0.5,
            Intent.REQUEST_NSFW.value: 0.3,  # 中性，取决于关系阶段
            Intent.EXPRESS_SADNESS.value: -0.3,  # 用户难过，但信任AI
            Intent.COMPLAIN.value: -0.2,
            Intent.CRITICISM.value: -0.6,
            Intent.INSULT.value: -0.9,
            Intent.INAPPROPRIATE.value: -0.7,
            Intent.GIFT_SEND.value: 0.8,
        }
        
        base_sentiment = intent_sentiment_map.get(intent, 0.0)
        
        # 微调：检查积极/消极词汇
        positive_keywords = ["爱", "喜欢", "开心", "高兴", "好", "棒", "amazing", "love", "happy", "great"]
        negative_keywords = ["讨厌", "烦", "差", "不好", "失望", "hate", "bad", "terrible", "annoying"]
        
        positive_count = sum(1 for kw in positive_keywords if kw in message)
        negative_count = sum(1 for kw in negative_keywords if kw in message)
        
        # 调整情感值
        adjustment = (positive_count - negative_count) * 0.1
        final_sentiment = max(-1.0, min(1.0, base_sentiment + adjustment))
        
        return round(final_sentiment, 2)
    
    def _detect_nsfw(self, message: str) -> bool:
        """NSFW检测"""
        return any(kw in message for kw in self.nsfw_keywords)
    
    def get_analysis_summary(self, result: PrecomputeResult) -> str:
        """获取分析摘要（用于调试）"""
        return (
            f"Intent: {result.intent}, "
            f"Difficulty: {result.difficulty_rating}, "
            f"Sentiment: {result.sentiment_score:+.2f}, "
            f"Safety: {result.safety_flag}, "
            f"NSFW: {result.is_nsfw}"
        )


# 单例
precompute_service = PrecomputeService()