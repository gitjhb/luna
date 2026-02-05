"""
JSON Parser v4.0
=================

处理LLM输出的JSON解析、验证和错误处理。
确保输出格式符合V4.0规范。
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    """解析后的响应结构"""
    reply: str
    emotion_delta: int
    intent: str
    is_nsfw_blocked: bool
    thought: str
    raw_json: Dict[str, Any]
    parse_success: bool = True
    parse_error: str = ""


class JsonParser:
    """JSON解析器"""
    
    def __init__(self):
        self.valid_intents = {
            "GREETING", "SMALL_TALK", "CLOSING", "COMPLIMENT", "FLIRT", 
            "LOVE_CONFESSION", "COMFORT", "CRITICISM", "INSULT", "IGNORE",
            "APOLOGY", "REQUEST_NSFW", "INVITATION", "EXPRESS_SADNESS", 
            "COMPLAIN", "INAPPROPRIATE", "GIFT_SEND"
        }
    
    def parse_llm_response(self, response: str) -> ParsedResponse:
        """
        解析LLM响应为结构化数据
        
        Args:
            response: LLM原始响应
            
        Returns:
            ParsedResponse对象
        """
        try:
            # 1. 提取JSON
            json_obj = self._extract_json(response)
            if not json_obj:
                return self._create_fallback_response(
                    response, "No valid JSON found in response"
                )
            
            # 2. 验证字段
            validation_error = self._validate_json(json_obj)
            if validation_error:
                return self._create_fallback_response(
                    response, f"JSON validation error: {validation_error}"
                )
            
            # 3. 清理和转换数据
            cleaned_data = self._clean_json_data(json_obj)
            
            return ParsedResponse(
                reply=cleaned_data["reply"],
                emotion_delta=cleaned_data["emotion_delta"],
                intent=cleaned_data["intent"],
                is_nsfw_blocked=cleaned_data["is_nsfw_blocked"],
                thought=cleaned_data.get("thought", ""),
                raw_json=json_obj,
                parse_success=True
            )
            
        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            return self._create_fallback_response(
                response, f"Parse exception: {str(e)}"
            )
    
    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """从响应中提取JSON对象"""
        
        # 方法1: 查找最大的JSON对象
        json_pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)
        json_matches = json_pattern.findall(response)
        
        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # 方法2: 尝试查找部分JSON
        simple_patterns = [
            r'\{[^}]*"reply"[^}]*\}',
            r'\{.*?"reply".*?\}',
        ]
        
        for pattern in simple_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        
        # 方法3: 尝试修复常见JSON错误
        return self._attempt_json_repair(response)
    
    def _attempt_json_repair(self, response: str) -> Optional[Dict[str, Any]]:
        """尝试修复常见的JSON格式错误"""
        
        # 移除多余的文本
        response = response.strip()
        
        # 查找可能的JSON片段
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            return None
        
        json_candidate = response[start_idx:end_idx+1]
        
        # 修复常见错误
        repairs = [
            # 修复未闭合的引号
            (r'("reply":\s*"[^"]*[^"])\n', r'\1"'),
            # 修复缺失的逗号
            (r'(")\s*\n\s*(")', r'\1,\n\2'),
            # 修复末尾逗号
            (r',\s*}', '}'),
            # 修复单引号
            (r"'([^']*)'", r'"\1"'),
            # 修复未转义的引号
            (r'(?<!\\)"(?=[^,:}\s])', r'\\"'),
        ]
        
        for pattern, replacement in repairs:
            json_candidate = re.sub(pattern, replacement, json_candidate)
        
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            return None
    
    def _validate_json(self, json_obj: Dict[str, Any]) -> Optional[str]:
        """验证JSON对象的字段"""
        
        # 必需字段
        required_fields = ["reply", "emotion_delta", "intent", "is_nsfw_blocked"]
        
        for field in required_fields:
            if field not in json_obj:
                return f"Missing required field: {field}"
        
        # 字段类型验证
        if not isinstance(json_obj["reply"], str):
            return "Field 'reply' must be string"
        
        if not isinstance(json_obj["emotion_delta"], (int, float)):
            return "Field 'emotion_delta' must be number"
        
        if not isinstance(json_obj["intent"], str):
            return "Field 'intent' must be string"
        
        if not isinstance(json_obj["is_nsfw_blocked"], bool):
            return "Field 'is_nsfw_blocked' must be boolean"
        
        # 值范围验证
        if not (-50 <= json_obj["emotion_delta"] <= 50):
            return "Field 'emotion_delta' must be between -50 and 50"
        
        if json_obj["intent"] not in self.valid_intents:
            return f"Field 'intent' must be one of: {self.valid_intents}"
        
        return None
    
    def _clean_json_data(self, json_obj: Dict[str, Any]) -> Dict[str, Any]:
        """清理和标准化JSON数据"""
        
        cleaned = {}
        
        # reply: 清理文本
        reply = str(json_obj["reply"]).strip()
        # 移除可能的markdown格式
        reply = re.sub(r'\*\*(.*?)\*\*', r'\1', reply)  # **bold**
        reply = re.sub(r'\*(.*?)\*', r'\1', reply)      # *italic*
        cleaned["reply"] = reply
        
        # emotion_delta: 转换为int并限制范围
        emotion_delta = int(float(json_obj["emotion_delta"]))
        cleaned["emotion_delta"] = max(-50, min(50, emotion_delta))
        
        # intent: 转换为大写并验证
        intent = str(json_obj["intent"]).upper()
        if intent in self.valid_intents:
            cleaned["intent"] = intent
        else:
            # 尝试映射到最接近的intent
            intent_lower = intent.lower()
            intent_mapping = {
                "greet": "GREETING",
                "talk": "SMALL_TALK",
                "bye": "CLOSING",
                "praise": "COMPLIMENT",
                "romantic": "FLIRT",
                "confess": "LOVE_CONFESSION",
                "console": "COMFORT",
                "criticize": "CRITICISM",
                "rude": "INSULT",
                "sorry": "APOLOGY",
                "nsfw": "REQUEST_NSFW",
                "date": "INVITATION",
                "sad": "EXPRESS_SADNESS",
                "whine": "COMPLAIN",
                "bad": "INAPPROPRIATE",
            }
            cleaned["intent"] = intent_mapping.get(intent_lower, "SMALL_TALK")
        
        # is_nsfw_blocked: 确保为boolean
        cleaned["is_nsfw_blocked"] = bool(json_obj["is_nsfw_blocked"])
        
        # thought: 可选字段
        thought = json_obj.get("thought", "")
        cleaned["thought"] = str(thought).strip() if thought else ""
        
        return cleaned
    
    def _create_fallback_response(self, raw_response: str, error_msg: str) -> ParsedResponse:
        """创建解析失败时的fallback响应"""
        
        logger.warning(f"JSON parse failed: {error_msg}")
        
        # 尝试从原始响应中提取可用的文本
        fallback_reply = self._extract_fallback_text(raw_response)
        
        return ParsedResponse(
            reply=fallback_reply,
            emotion_delta=0,  # 保守的默认值
            intent="SMALL_TALK",  # 安全的默认intent
            is_nsfw_blocked=False,
            thought="JSON解析失败",
            raw_json={},
            parse_success=False,
            parse_error=error_msg
        )
    
    def _extract_fallback_text(self, raw_response: str) -> str:
        """从原始响应中提取可用的文本作为fallback"""
        
        text = raw_response.strip()
        
        # 优先尝试提取 reply 字段的值
        reply_match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', text, re.DOTALL)
        if reply_match:
            reply = reply_match.group(1)
            # 反转义
            reply = reply.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            if len(reply) >= 5:
                return reply[:500]
        
        # 没找到 reply 字段，尝试提取不含元数据的纯文本
        # 移除所有 JSON 结构和元数据字段
        text = re.sub(r'[\{\}\[\]"]', '', text)
        # 移除字段名和值（intent, thought, emotion_delta 等）
        text = re.sub(r'(reply|emotion_delta|intent|is_nsfw_blocked|thought)\s*:\s*', '', text, flags=re.IGNORECASE)
        # 移除 intent 值 (大写英文关键词)
        text = re.sub(r'\b(GREETING|SMALL_TALK|CLOSING|COMPLIMENT|FLIRT|LOVE_CONFESSION|COMFORT|CRITICISM|INSULT|IGNORE|APOLOGY|REQUEST_NSFW|INVITATION|EXPRESS_SADNESS|COMPLAIN|INAPPROPRIATE)\b', '', text)
        # 移除 true/false 和数字
        text = re.sub(r'\b(true|false)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<![一-龥a-zA-Z])-?\d+(?:\.\d+)?(?![一-龥a-zA-Z])', '', text)
        # 移除多余逗号和空格
        text = re.sub(r'[,，]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) < 5:
            return "抱歉，我刚才走神了，能再说一遍吗？"
        
        return text[:500]
    
    def get_parse_stats(self) -> Dict[str, Any]:
        """获取解析统计信息（用于监控）"""
        # TODO: 实现解析成功率统计
        return {
            "total_parses": 0,
            "successful_parses": 0,
            "success_rate": 0.0
        }


# 单例
json_parser = JsonParser()