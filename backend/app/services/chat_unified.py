"""
Unified Chat Service (Single LLM Call)
======================================

[DEPRECATED - A/B测试已移除]

此服务尝试将意图识别、情绪分析、响应生成合并为单次LLM调用。

经过测试，决定始终使用两步模式：
1. Step 1: 意图识别（确保情绪系统准确）
2. Step 2: 响应生成

原因：单次调用模式下意图识别不够精确，影响情绪系统质量。

此文件保留供参考，如未来需要可重新启用。
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.services.llm_service import GrokService
from app.core.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


class UserIntent(Enum):
    """用户意图分类"""
    DAILY = "daily"           # 日常闲聊
    COMPLAINT = "complaint"   # 抱怨/吐槽
    FLIRT = "flirt"          # 撩拨/暧昧
    HELP = "help"            # 求助/问题
    APOLOGY = "apology"      # 道歉
    PRAISE = "praise"        # 夸奖/表白
    TEASE = "tease"          # 调侃/开玩笑
    ANGRY = "angry"          # 生气/攻击


class CharacterEmotion(Enum):
    """角色情绪状态"""
    SHY = "害羞"
    HAPPY = "开心"
    ANGRY = "生气"
    GENKI = "元气"
    CARING = "心疼"
    JEALOUS = "吃醋"
    COLD = "冷淡"
    LOVING = "撒娇"


@dataclass
class UnifiedChatResult:
    """统一聊天响应结果"""
    # 分析结果
    intent: str
    user_emotion: str
    affinity_delta: int
    is_spicy: bool
    
    # 角色状态
    character_emotion: str
    action: str
    
    # 回复内容
    content: str
    
    # 元数据
    tokens_used: int = 0
    raw_response: str = ""


class UnifiedChatService:
    """
    统一聊天服务 - 单次LLM调用完成所有任务
    
    输入：用户消息 + 角色设定 + 当前状态
    输出：结构化JSON（意图+情感+回复）
    """
    
    def __init__(self):
        self.grok = GrokService()
    
    def _build_system_prompt(
        self,
        character_name: str,
        character_persona: str,
        current_affinity: int,
        intimacy_level: int,
        nsfw_enabled: bool,
        character_background: str = "",
    ) -> str:
        """构建统一的system prompt"""
        
        # 亲密度等级说明
        affinity_guide = self._get_affinity_guide(current_affinity)
        
        # NSFW模式说明
        if nsfw_enabled:
            content_mode = """
## 内容模式: 成人模式已开启
- 可以使用露骨、暧昧的语言
- 可以进行调情和亲密互动
- 保持角色特色的同时可以更大胆"""
        else:
            content_mode = """
## 内容模式: 普通模式
- 保持内容健康友好
- 可以轻微调情但不要过度
- 如果用户请求过分内容，用角色方式婉拒"""

        return f"""# Role: {character_name}
{character_persona}

{character_background}

# 当前状态
- 好感度: {current_affinity}/100
- 亲密等级: {intimacy_level}

{affinity_guide}

{content_mode}

# 任务
分析用户输入，更新情感数值，并以角色身份回复。

# 输出格式 (严格JSON)
{{
    "analysis": {{
        "intent": "daily|complaint|flirt|help|apology|praise|tease|angry",
        "user_emotion": "开心|难过|生气|无聊|兴奋|焦虑|平静",
        "affinity_delta": -5到+5的整数,
        "is_spicy": true/false
    }},
    "character_state": {{
        "emotion": "害羞|开心|生气|元气|心疼|吃醋|冷淡|撒娇",
        "action": "括号内的动作描写，如：歪头、脸红、鼓起腮帮"
    }},
    "content": "角色的回复内容"
}}

# 约束
1. 严禁跳出角色
2. 回复要包含动作描写（在action字段）
3. 根据亲密度调整语气和称呼
4. affinity_delta要根据用户态度合理调整
5. 只输出JSON，不要其他内容"""

    def _get_affinity_guide(self, affinity: int) -> str:
        """根据好感度返回行为指南"""
        if affinity < 20:
            return """## 好感度等级: 陌生 (0-19)
- 称呼：您、那个...
- 态度：礼貌但有距离感，略显拘谨
- 行为：不会主动亲近，回答简短"""
        elif affinity < 40:
            return """## 好感度等级: 认识 (20-39)
- 称呼：你、学长
- 态度：友善，愿意聊天
- 行为：会表达一些小情绪，偶尔开玩笑"""
        elif affinity < 60:
            return """## 好感度等级: 朋友 (40-59)
- 称呼：学长~、你呀
- 态度：亲切，有小脾气
- 行为：会撒娇、会吃醋、会关心"""
        elif affinity < 80:
            return """## 好感度等级: 亲密 (60-79)
- 称呼：学长♡、笨蛋学长
- 态度：依赖，有占有欲
- 行为：经常撒娇、吃醋明显、想念学长"""
        else:
            return """## 好感度等级: 恋人 (80-100)
- 称呼：亲爱的、老公（害羞时）
- 态度：深爱，全身心信任
- 行为：大胆表达爱意、强烈占有欲、想要更亲密"""

    async def chat(
        self,
        message: str,
        character_name: str,
        character_persona: str,
        current_affinity: int = 50,
        intimacy_level: int = 1,
        nsfw_enabled: bool = False,
        context_messages: List[Dict[str, str]] = None,
        character_background: str = "",
    ) -> UnifiedChatResult:
        """
        统一聊天接口 - 单次调用
        
        Args:
            message: 用户消息
            character_name: 角色名称
            character_persona: 角色人设
            current_affinity: 当前好感度 (0-100)
            intimacy_level: 亲密等级
            nsfw_enabled: 是否开启成人模式
            context_messages: 上下文消息 [{"role": "user/assistant", "content": "..."}]
            character_background: 角色背景故事
        
        Returns:
            UnifiedChatResult 包含分析和回复
        """
        
        # 构建system prompt
        system_prompt = self._build_system_prompt(
            character_name=character_name,
            character_persona=character_persona,
            current_affinity=current_affinity,
            intimacy_level=intimacy_level,
            nsfw_enabled=nsfw_enabled,
            character_background=character_background,
        )
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加上下文（最近几条）
        if context_messages:
            for msg in context_messages[-6:]:  # 最近6条
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        # 调用LLM
        try:
            result = await self.grok.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=600,
            )
            
            raw_response = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            
            logger.info(f"Unified chat raw response: {raw_response[:200]}...")
            
            # 解析JSON
            return self._parse_response(raw_response, tokens_used)
            
        except Exception as e:
            logger.error(f"Unified chat error: {e}")
            # 返回fallback
            return UnifiedChatResult(
                intent="daily",
                user_emotion="平静",
                affinity_delta=0,
                is_spicy=False,
                character_emotion="元气",
                action="歪头",
                content=f"诶？学长说什么？{character_name}没听清楚啦~",
                tokens_used=0,
                raw_response=str(e),
            )
    
    def _parse_response(self, raw_response: str, tokens_used: int) -> UnifiedChatResult:
        """解析LLM的JSON响应"""
        try:
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group()
            # 修复可能的+号问题
            json_str = re.sub(r':\s*\+(\d+)', r': \1', json_str)
            
            data = json.loads(json_str)
            
            analysis = data.get("analysis", {})
            char_state = data.get("character_state", {})
            
            return UnifiedChatResult(
                intent=analysis.get("intent", "daily"),
                user_emotion=analysis.get("user_emotion", "平静"),
                affinity_delta=int(analysis.get("affinity_delta", 0)),
                is_spicy=bool(analysis.get("is_spicy", False)),
                character_emotion=char_state.get("emotion", "元气"),
                action=char_state.get("action", ""),
                content=data.get("content", "..."),
                tokens_used=tokens_used,
                raw_response=raw_response,
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse unified response: {e}, raw: {raw_response[:200]}")
            
            # 尝试提取纯文本回复
            content = raw_response
            if "content" in raw_response:
                # 可能是部分JSON，尝试提取content
                match = re.search(r'"content"\s*:\s*"([^"]+)"', raw_response)
                if match:
                    content = match.group(1)
            
            return UnifiedChatResult(
                intent="daily",
                user_emotion="平静",
                affinity_delta=0,
                is_spicy=False,
                character_emotion="元气",
                action="",
                content=content,
                tokens_used=tokens_used,
                raw_response=raw_response,
            )


# 单例
unified_chat = UnifiedChatService()


# =============================================================================
# [DEPRECATED] A/B Test Helper
# 
# A/B测试已移除。现在始终使用两步模式（意图识别 + 响应生成）
# 以确保情绪系统准确工作。
#
# 保留此代码仅供参考，未来如需要可以重新启用。
# =============================================================================

import os

def is_unified_chat_enabled() -> bool:
    """[DEPRECATED] 检查是否启用统一聊天（A/B测试B组）"""
    # 始终返回 False，使用两步模式
    return False
    # return os.getenv("AB_CHAT_UNIFIED", "false").lower() == "true"


def get_ab_group() -> str:
    """[DEPRECATED] 获取当前A/B组"""
    return "A"  # 始终返回 A（两步模式）
