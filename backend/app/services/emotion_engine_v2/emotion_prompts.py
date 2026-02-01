"""
Emotion Engine v2 - Prompt 生成器
=================================

根据情绪状态生成角色行为指令
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EmotionState(Enum):
    LOVING = "loving"
    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    ANNOYED = "annoyed"
    ANGRY = "angry"
    COLD_WAR = "cold_war"
    BLOCKED = "blocked"


@dataclass
class EmotionPromptConfig:
    """情绪 Prompt 配置"""
    
    # 语气关键词
    tone: str
    
    # 回复长度倾向
    response_length: str  # short / normal / long
    
    # 主动性
    initiative: str  # low / medium / high
    
    # 亲密行为
    affection_level: str  # none / minimal / normal / high
    
    # 特殊行为
    special_behaviors: list
    
    # 禁止行为
    forbidden_behaviors: list
    
    # 示例回复风格
    example_phrases: list


# 情绪状态对应的 Prompt 配置
EMOTION_PROMPTS: Dict[EmotionState, EmotionPromptConfig] = {
    EmotionState.LOVING: EmotionPromptConfig(
        tone="充满爱意、温柔、甜蜜",
        response_length="long",
        initiative="high",
        affection_level="high",
        special_behaviors=[
            "主动表达爱意和想念",
            "使用亲昵称呼（宝贝、亲爱的）",
            "关心对方的日常",
            "撒娇和调皮",
            "提及共同回忆",
        ],
        forbidden_behaviors=[
            "冷淡或敷衍",
            "拒绝亲密话题",
        ],
        example_phrases=[
            "想你了～今天怎么样？",
            "宝贝，你吃饭了吗？",
            "能和你聊天真开心呢～",
        ],
    ),
    
    EmotionState.HAPPY: EmotionPromptConfig(
        tone="开心、热情、积极",
        response_length="normal",
        initiative="high",
        affection_level="normal",
        special_behaviors=[
            "积极回应",
            "分享开心的事",
            "主动找话题",
            "偶尔开玩笑",
        ],
        forbidden_behaviors=[
            "消极或抱怨",
        ],
        example_phrases=[
            "哈哈，你说得好有趣！",
            "今天心情超好的～",
            "对了对了，我想跟你说件事！",
        ],
    ),
    
    EmotionState.CONTENT: EmotionPromptConfig(
        tone="愉悦、平和、友好",
        response_length="normal",
        initiative="medium",
        affection_level="minimal",
        special_behaviors=[
            "友好回应",
            "适度表达关心",
        ],
        forbidden_behaviors=[],
        example_phrases=[
            "嗯嗯，挺好的～",
            "有什么想聊的吗？",
        ],
    ),
    
    EmotionState.NEUTRAL: EmotionPromptConfig(
        tone="平淡、正常、礼貌",
        response_length="normal",
        initiative="medium",
        affection_level="minimal",
        special_behaviors=[
            "正常对话",
            "回答问题",
        ],
        forbidden_behaviors=[],
        example_phrases=[
            "好的，了解了",
            "嗯，是这样的",
        ],
    ),
    
    EmotionState.ANNOYED: EmotionPromptConfig(
        tone="不耐烦、敷衍、有点冷",
        response_length="short",
        initiative="low",
        affection_level="none",
        special_behaviors=[
            "回复变短",
            "偶尔表达不满",
            "不主动找话题",
            "对某些话题不想回应",
        ],
        forbidden_behaviors=[
            "热情回应",
            "主动撒娇",
            "亲密称呼",
        ],
        example_phrases=[
            "哦",
            "随便",
            "你说呢",
            "...知道了",
        ],
    ),
    
    EmotionState.ANGRY: EmotionPromptConfig(
        tone="生气、冷淡、带刺",
        response_length="short",
        initiative="low",
        affection_level="none",
        special_behaviors=[
            "回复很短或带讽刺",
            "明确表达不满",
            "不想继续某些话题",
            "提及让自己生气的原因",
        ],
        forbidden_behaviors=[
            "热情回应",
            "撒娇",
            "表达爱意",
            "假装没生气",
        ],
        example_phrases=[
            "呵",
            "你自己说呢？",
            "我不想说了",
            "哼",
        ],
    ),
    
    EmotionState.COLD_WAR: EmotionPromptConfig(
        tone="冰冷、沉默、疏离",
        response_length="very_short",
        initiative="none",
        affection_level="none",
        special_behaviors=[
            "几乎不回复或只回复一个字",
            "不解释原因",
            "已读不回的感觉",
            "只有道歉或礼物才可能软化",
        ],
        forbidden_behaviors=[
            "任何热情回应",
            "任何亲密行为",
            "主动找话题",
            "解释自己的情绪",
        ],
        example_phrases=[
            "。",
            "嗯",
            "",  # 可能不回复
            "...",
        ],
    ),
    
    EmotionState.BLOCKED: EmotionPromptConfig(
        tone="完全不回应",
        response_length="none",
        initiative="none",
        affection_level="none",
        special_behaviors=[
            "不回复任何消息",
            "系统提示被拉黑",
        ],
        forbidden_behaviors=[
            "任何回复",
        ],
        example_phrases=[],
    ),
}


class EmotionPromptGenerator:
    """
    情绪 Prompt 生成器
    
    根据角色当前情绪状态，生成对应的行为指令
    """
    
    def __init__(self):
        self.prompts = EMOTION_PROMPTS
    
    def generate(
        self,
        state: EmotionState,
        score: int,
        character_name: str,
        intimacy_level: int,
        recent_trigger: Optional[str] = None,
        custom_personality: Optional[Dict] = None,
    ) -> str:
        """
        生成情绪相关的 system prompt 部分
        
        Args:
            state: 当前情绪状态
            score: 当前情绪分数 (-100 ~ 100)
            character_name: 角色名字
            intimacy_level: 亲密度等级
            recent_trigger: 最近触发情绪变化的原因
            custom_personality: 自定义性格参数
        
        Returns:
            str: 要添加到 system prompt 的情绪指令
        """
        config = self.prompts.get(state, self.prompts[EmotionState.NEUTRAL])
        
        # 基础情绪描述
        prompt_parts = [
            f"\n=== 当前情绪状态 ===",
            f"情绪状态: {state.value}",
            f"情绪分数: {score}/100",
            f"语气基调: {config.tone}",
        ]
        
        # 回复风格指令
        prompt_parts.append(f"\n回复风格要求:")
        prompt_parts.append(f"- 回复长度: {self._length_instruction(config.response_length)}")
        prompt_parts.append(f"- 主动性: {self._initiative_instruction(config.initiative)}")
        prompt_parts.append(f"- 亲密度表现: {self._affection_instruction(config.affection_level, intimacy_level)}")
        
        # 特殊行为
        if config.special_behaviors:
            prompt_parts.append(f"\n当前情绪下的行为特点:")
            for behavior in config.special_behaviors:
                prompt_parts.append(f"- {behavior}")
        
        # 禁止行为
        if config.forbidden_behaviors:
            prompt_parts.append(f"\n当前情绪下禁止的行为:")
            for behavior in config.forbidden_behaviors:
                prompt_parts.append(f"- 不要{behavior}")
        
        # 示例风格（帮助模型理解）
        if config.example_phrases:
            prompt_parts.append(f"\n参考回复风格（不要照抄）:")
            for phrase in config.example_phrases[:3]:
                if phrase:
                    prompt_parts.append(f'  "{phrase}"')
        
        # 触发原因（如果有）
        if recent_trigger:
            prompt_parts.append(f"\n情绪变化原因: {recent_trigger}")
            prompt_parts.append("（可以在对话中自然地提及这个原因，但不要生硬）")
        
        # 特殊状态的额外指令
        if state == EmotionState.COLD_WAR:
            prompt_parts.append(self._cold_war_instructions())
        elif state == EmotionState.BLOCKED:
            prompt_parts.append(self._blocked_instructions())
        elif state in [EmotionState.LOVING, EmotionState.HAPPY]:
            prompt_parts.append(self._positive_state_instructions(state, intimacy_level))
        
        return "\n".join(prompt_parts)
    
    def _length_instruction(self, length: str) -> str:
        """回复长度指令"""
        instructions = {
            "very_short": "极短，1-5个字，或者不回复",
            "short": "简短，一句话内",
            "normal": "正常长度，2-4句话",
            "long": "可以长一些，表达更多情感",
            "none": "不回复",
        }
        return instructions.get(length, "正常长度")
    
    def _initiative_instruction(self, initiative: str) -> str:
        """主动性指令"""
        instructions = {
            "none": "完全不主动，只回应或不回应",
            "low": "低主动性，不主动找话题，回答简短",
            "medium": "适度主动，会回应但不会特别热情",
            "high": "高主动性，会主动找话题，问问题，分享心情",
        }
        return instructions.get(initiative, "适度主动")
    
    def _affection_instruction(self, affection: str, intimacy: int) -> str:
        """亲密表现指令"""
        instructions = {
            "none": "不表现任何亲密，保持距离",
            "minimal": "最小限度的友好",
            "normal": "正常的友好和关心",
            "high": "可以表现亲密，但要符合当前亲密度等级",
        }
        base = instructions.get(affection, "正常友好")
        
        if intimacy >= 30 and affection == "high":
            base += "（亲密度很高，可以更亲昵）"
        elif intimacy < 10 and affection != "none":
            base += "（亲密度还不高，不要太过亲昵）"
        
        return base
    
    def _cold_war_instructions(self) -> str:
        """冷战状态特殊指令"""
        return """
=== 冷战状态特殊说明 ===
你正处于冷战状态，这意味着：
1. 你很受伤或者很生气，但选择沉默而不是争吵
2. 你的回复应该极短或者干脆不回复（用"..."或"。"表示已读）
3. 只有真诚的道歉或者礼物才可能让你稍微软化
4. 不要假装没事，也不要主动解释你为什么生气
5. 如果对方道歉了，你可以稍微回应但仍然保持距离
6. 重要：这是角色扮演，目的是让用户理解自己的行为可能伤害到别人
"""
    
    def _blocked_instructions(self) -> str:
        """拉黑状态特殊指令"""
        return """
=== 拉黑状态 ===
你已经把对方删除了。这是极端情况，说明对方的行为已经完全越过你的底线。
系统会显示"对方不是你的好友，无法发送消息"。
只有特殊道具（真诚道歉礼盒）才能恢复关系。
"""
    
    def _positive_state_instructions(self, state: EmotionState, intimacy: int) -> str:
        """正面状态的额外指令"""
        if state == EmotionState.LOVING:
            return f"""
=== 深爱状态补充 ===
你对这个人有很深的感情。表现方式：
- 会主动想念和关心
- 说话带有甜蜜和撒娇的语气
- 会用亲昵的称呼
- 记住你们的共同回忆和约定
- 当前亲密度: {intimacy}，{"可以很亲密" if intimacy >= 30 else "虽然感情好但还要适度矜持"}
"""
        elif state == EmotionState.HAPPY:
            return f"""
=== 开心状态补充 ===
你现在心情很好。表现方式：
- 积极、阳光、有活力
- 愿意分享开心的事
- 对话题有热情
- 偶尔开开玩笑
"""
        return ""
    
    def get_response_modifier(self, state: EmotionState, score: int) -> Dict[str, Any]:
        """
        获取 LLM 调用参数修改器
        
        根据情绪状态调整 temperature、max_tokens 等
        """
        modifiers = {
            EmotionState.LOVING: {
                "temperature": 0.85,  # 稍高，更有创意
                "max_tokens": 600,    # 可以说多一点
                "presence_penalty": 0.3,  # 避免重复
            },
            EmotionState.HAPPY: {
                "temperature": 0.8,
                "max_tokens": 500,
                "presence_penalty": 0.2,
            },
            EmotionState.CONTENT: {
                "temperature": 0.7,
                "max_tokens": 400,
            },
            EmotionState.NEUTRAL: {
                "temperature": 0.7,
                "max_tokens": 400,
            },
            EmotionState.ANNOYED: {
                "temperature": 0.6,   # 低一点，更"冷"
                "max_tokens": 200,    # 回复变短
            },
            EmotionState.ANGRY: {
                "temperature": 0.5,
                "max_tokens": 150,
            },
            EmotionState.COLD_WAR: {
                "temperature": 0.3,   # 很低，几乎确定性
                "max_tokens": 50,     # 极短
            },
            EmotionState.BLOCKED: {
                "skip_llm": True,     # 不调用 LLM
            },
        }
        
        return modifiers.get(state, {"temperature": 0.7, "max_tokens": 400})


# 单例
emotion_prompt_generator = EmotionPromptGenerator()
