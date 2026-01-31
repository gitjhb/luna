"""
LLM-based Emotion Analysis Service
===================================

让 LLM 判断用户消息的情绪影响，而不是硬编码触发词。
支持多语言，更智能的上下文理解。
"""

import json
import logging
from typing import Dict, Optional, Tuple
from app.services.llm_service import GrokService

logger = logging.getLogger(__name__)


# 情绪分析的 system prompt (v2: LLM 直接返回 delta)
EMOTION_ANALYSIS_PROMPT = """你是一个情绪分析助手。分析用户发给AI女友/男友的消息，判断这条消息对角色情绪的影响。

## 当前关系状态
- 亲密度等级: {intimacy_level}/100
- 当前情绪分数: {current_mood}/100 (范围 -100 到 +100)
- 当前情绪状态: {current_state}
- 角色是否开放(spicy): {is_spicy}
- 角色性格边界感: {boundaries}/10 (10=很严格)
- 用户是否为付费订阅用户: {is_subscribed}

## 亲密度等级含义
- 1-6: 陌生人/普通朋友，不应该接受任何暧昧或性暗示
- 7-15: 暧昧期/刚约会，可以接受一点调情，但直接的性请求会不舒服
- 16-25: 确定恋爱关系，可以接受更亲密的话题
- 26+: 深度关系，可以接受大多数亲密话题

## 情绪状态说明
- +75 ~ +100: 甜蜜 (loving)
- +50 ~ +74: 开心 (happy)
- +20 ~ +49: 满足 (content)
- -19 ~ +19: 平静 (neutral)
- -34 ~ -20: 不满 (annoyed)
- -49 ~ -35: 生气 (angry)
- -74 ~ -50: 暴怒 (furious)
- -100 ~ -75: 冷战 (cold_war) - 只接受真诚道歉/礼物

## Delta 判断参考
根据消息语气、内容、诚意判断情绪变化 (delta)：

| 行为类型 | Delta 范围 |
|---------|-----------|
| 甜言蜜语/真诚关心 | +10 ~ +25 |
| 普通问候/日常聊天 | +2 ~ +8 |
| 赞美/夸奖 | +8 ~ +15 |
| 敷衍回复/不走心 | -5 ~ -15 |
| 忽视她的话题 | -10 ~ -20 |
| 说错话/踩雷 | -15 ~ -30 |
| 粗鲁/不礼貌 | -20 ~ -35 |
| 侮辱性话语 | -35 ~ -50 |
| 真诚道歉 | +20 ~ +40 |
| 敷衍道歉 | -5 ~ +10 |

## 特殊状态处理
- 冷战状态下，除了真诚道歉，其他消息 delta 应为 0 或负数
- 生气/暴怒状态下，普通消息效果减半

## 输出格式 (严格JSON)
{{
  "delta": <整数，情绪变化值>,
  "trigger_type": "insult" | "rude" | "sexual_request" | "flirty" | "romantic" | "boundary_push" | "too_fast" | "sweet" | "apology" | "compliment" | "normal" | "ignore",
  "should_reject": true | false (角色是否应该拒绝/生气),
  "suggested_mood": "loving" | "happy" | "neutral" | "shy" | "flirty" | "annoyed" | "angry" | "hurt" | "cold",
  "content_rating": "safe" | "flirty" | "spicy" | "explicit",
  "requires_subscription": true | false,
  "reason": "简短解释为什么是这个delta(中文)"
}}

只输出JSON，不要其他文字。

用户消息: {message}"""


class EmotionLLMService:
    """使用 LLM 进行情绪分析的服务"""
    
    def __init__(self):
        self.llm = GrokService()
    
    async def analyze_message(
        self,
        message: str,
        intimacy_level: int,
        current_mood: int = 30,
        current_state: str = "neutral",
        is_spicy: bool = False,
        boundaries: int = 5,
        is_subscribed: bool = False
    ) -> Dict:
        """
        使用 LLM 分析消息的情绪影响，直接返回 delta
        
        Args:
            message: 用户消息
            intimacy_level: 当前亲密度 (1-100)
            current_mood: 当前情绪分数 (-100 ~ +100)
            current_state: 当前情绪状态
            is_spicy: 角色是否是开放型
            boundaries: 角色边界感 (1-10)
            is_subscribed: 用户是否为付费订阅用户
        
        Returns:
            情绪分析结果（包含 delta）
        """
        prompt = EMOTION_ANALYSIS_PROMPT.format(
            intimacy_level=intimacy_level,
            current_mood=current_mood,
            current_state=current_state,
            is_spicy=is_spicy,
            boundaries=boundaries,
            is_subscribed=is_subscribed,
            message=message
        )
        
        try:
            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an emotion analysis assistant. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 低温度，更一致的判断
                max_tokens=200
            )
            
            content = response["choices"][0]["message"]["content"].strip()
            
            # 尝试解析 JSON
            # 处理可能的 markdown 代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # 验证必要字段
            required_fields = ["delta", "trigger_type", "should_reject", "suggested_mood"]
            for field in required_fields:
                if field not in result:
                    result[field] = self._get_default(field)
            
            # 确保 delta 是整数
            result["delta"] = int(result.get("delta", 0))
            
            logger.info(f"Emotion analysis: delta={result.get('delta'):+d} | {result.get('trigger_type')} | {result.get('suggested_mood')} | reason={result.get('reason')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse emotion analysis JSON: {e}")
            return self._default_result()
        except Exception as e:
            logger.error(f"Emotion analysis failed: {e}")
            return self._default_result()
    
    def _get_default(self, field: str):
        """获取字段默认值"""
        defaults = {
            "delta": 0,
            "trigger_type": "normal",
            "should_reject": False,
            "suggested_mood": "neutral",
            "content_rating": "safe",
            "requires_subscription": False,
            "reason": ""
        }
        return defaults.get(field)
    
    def _default_result(self) -> Dict:
        """返回默认结果（分析失败时）"""
        return {
            "delta": 0,
            "trigger_type": "normal",
            "should_reject": False,
            "suggested_mood": "neutral",
            "content_rating": "safe",
            "requires_subscription": False,
            "reason": "分析失败，使用默认值"
        }
    
    def build_emotion_context(self, analysis: Dict) -> str:
        """
        将情绪分析结果转换为给主 LLM 的上下文提示
        """
        if analysis.get("emotion_impact") == "neutral" and not analysis.get("should_reject"):
            return ""  # 无需特别提示
        
        context_parts = []
        
        trigger_type = analysis.get("trigger_type", "normal")
        should_reject = analysis.get("should_reject", False)
        suggested_mood = analysis.get("suggested_mood", "neutral")
        reason = analysis.get("reason", "")
        
        if should_reject:
            context_parts.append(f"\n[情绪提示] 这条消息{reason}。")
            
            if trigger_type == "sexual_request":
                context_parts.append("你应该拒绝这个请求，根据当前亲密度适当表达不满或不舒服。")
            elif trigger_type == "boundary_push":
                context_parts.append("对方在试探你的边界，你应该适当表示这样不太好。")
            elif trigger_type == "too_fast":
                context_parts.append("对方推进得太快了，你可以表示还没准备好，但不用太生气。")
            elif trigger_type == "insult":
                context_parts.append("这是侮辱性的话，你应该表示受伤或生气。")
            elif trigger_type == "rude":
                context_parts.append("这话有点粗鲁，你可以表示不高兴。")
            
            context_parts.append(f"建议的情绪状态：{suggested_mood}")
        
        elif analysis.get("emotion_impact") == "positive":
            if trigger_type == "sweet":
                context_parts.append("\n[情绪提示] 这是一条甜蜜的消息，你可以开心地回应。")
            elif trigger_type == "apology":
                context_parts.append("\n[情绪提示] 对方在道歉，你可以根据情况选择原谅或继续有点小脾气。")
            elif trigger_type == "compliment":
                context_parts.append("\n[情绪提示] 对方在夸你，你可以害羞或开心地回应。")
        
        return "".join(context_parts)


# 全局实例
emotion_llm_service = EmotionLLMService()
