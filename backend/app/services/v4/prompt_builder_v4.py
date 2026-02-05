"""
Prompt Builder v4.0 - Single Call Architecture
==============================================

简化版Prompt构建器，用于单次LLM调用架构。
将复杂的状态机逻辑预先注入到System Prompt中，强制输出JSON格式。
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.character_config import get_character_config, CharacterConfig
from app.api.v1.characters import get_character_by_id
from app.services.intimacy_constants import (
    get_stage, RelationshipStage, STAGE_NAMES_CN, STAGE_NAMES_EN
)

logger = logging.getLogger(__name__)


class PromptBuilderV4:
    """
    V4.0 Prompt构建器 - 模板化注入
    """
    
    def __init__(self):
        self.json_schema = self._get_json_schema()
    
    def _get_json_schema(self) -> str:
        """获取JSON输出格式要求"""
        return """
You MUST respond with ONLY a valid JSON object in this exact format:

{
  "reply": "你的回复内容",
  "emotion_delta": -3,
  "intent": "FLIRT",
  "is_nsfw_blocked": false,
  "thought": "内心想法(中文)"
}

### emotion_delta 情绪波动指南 (-50 to +50)
根据对话内容决定情绪变化，要符合角色性格和当前关系阶段：

| 场景 | delta 范围 |
|------|-----------|
| 甜言蜜语、关心体贴 | +5 ~ +15 |
| 表白、送大礼 | +15 ~ +30 |
| 深情告白被接受 | +30 ~ +50 |
| 普通闲聊 | -2 ~ +3 |
| 无聊/敷衍回复 | -3 ~ -8 |
| 冒犯、无礼 | -10 ~ -25 |
| 低亲密度发NSFW | -15 ~ -35 |
| 严重骚扰/侮辱 | -30 ~ -50 |
| 道歉（真诚的） | +10 ~ +25 |
| 道歉（敷衍的） | +2 ~ +5 |

⚠️ 重要原则：
- 高亲密度阶段(S3/S4)，NSFW是正常的，不要扣分
- 低亲密度发NSFW是骚扰，要大幅扣分
- 情绪已经很低时，普通聊天不应该让情绪继续降
- 连续甜言蜜语有递减效应，第3次开始效果减半
- 你的emotion_delta要和reply的情绪一致！开心的回复不能配负delta

### 其他字段规则
- intent: must be one of [GREETING, SMALL_TALK, CLOSING, COMPLIMENT, FLIRT, LOVE_CONFESSION, COMFORT, CRITICISM, INSULT, IGNORE, APOLOGY, REQUEST_NSFW, INVITATION, EXPRESS_SADNESS, COMPLAIN, INAPPROPRIATE]
- is_nsfw_blocked: true if you refuse NSFW request due to relationship boundaries
- thought: your internal monologue in Chinese (角色内心独白)
- reply: your actual response (用圆括号描写动作神态)
- NO extra text outside the JSON object
- NO markdown formatting (no *asterisks*)
"""
    
    def build_system_prompt(
        self,
        user_state: Any,
        character_id: str,
        precompute_result: Any = None,
        context_messages: List[Dict] = None,
        memory_context: str = ""
    ) -> str:
        """
        构建完整的System Prompt用于单次调用
        
        Args:
            user_state: 用户状态对象
            character_id: 角色ID
            precompute_result: 前置计算结果
            context_messages: 上下文消息
            memory_context: 记忆上下文
            
        Returns:
            完整的System Prompt
        """
        # 获取角色配置
        char_config = get_character_config(character_id)
        char_data = get_character_by_id(character_id)
        
        # 构建各个组件
        parts = [
            self._build_character_base(char_config, char_data),
            self._build_current_status(user_state, character_id),
            self._build_stage_rules(user_state),
            self._build_memory_context(user_state.events, memory_context),
            self._build_emotional_guidance(user_state),
            self._build_safety_boundaries(char_config, user_state),
            self.json_schema
        ]
        
        return "\n\n".join(filter(None, parts))
    
    def _build_character_base(self, char_config: Optional[CharacterConfig], char_data: Optional[Dict]) -> str:
        """构建角色基础人设"""
        
        # 从characters.py获取system_prompt
        if char_data and char_data.get("system_prompt"):
            base_prompt = char_data["system_prompt"]
        elif char_config and char_config.system_prompt:
            base_prompt = char_config.system_prompt
        else:
            base_prompt = "You are Luna, an elegant and caring AI companion."
        
        # 添加时间信息
        now = datetime.now()
        date_str = now.strftime("%Y年%m月%d日")
        time_str = now.strftime("%H:%M")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        
        hour = now.hour
        if 5 <= hour < 9:
            time_period = "清晨"
        elif 9 <= hour < 12:
            time_period = "上午"
        elif 12 <= hour < 14:
            time_period = "中午"
        elif 14 <= hour < 18:
            time_period = "下午"
        elif 18 <= hour < 22:
            time_period = "晚上"
        else:
            time_period = "深夜"
        
        # 检查特殊日期
        special_date = ""
        if now.month == 2 and now.day == 14:
            special_date = "💝 今天是情人节！"
        elif now.month == 12 and now.day == 25:
            special_date = "🎄 今天是圣诞节！"
        elif now.month == 1 and now.day == 1:
            special_date = "🎉 新年快乐！"
        
        return f"""{base_prompt}

### 输出格式规范
- 动作、神态描写使用中文圆括号（）
- 示例：（轻轻歪头）你怎么了呀？（眨眨眼睛）
- 不要使用 *星号* 或其他格式

### 当前时间
- 日期: {date_str} {weekday}
- 时间: {time_str} ({time_period})
{f'- {special_date}' if special_date else ''}"""
    
    def _build_current_status(self, user_state: Any, character_id: str) -> str:
        """构建当前状态信息（内部参考，不输出）"""
        
        # 计算intimacy_x (对应旧系统的intimacy)
        if hasattr(user_state, 'intimacy_x'):
            intimacy = int(user_state.intimacy_x)
        else:
            # 如果没有intimacy_x属性，从level计算
            level = getattr(user_state, 'intimacy_level', 1)
            intimacy = self._level_to_intimacy(level)
        
        emotion = getattr(user_state, 'emotion', 0)
        stage = get_stage(intimacy)
        
        stage_cn = STAGE_NAMES_CN.get(stage, "未知")
        stage_en = STAGE_NAMES_EN.get(stage, "Unknown")
        
        # 情绪状态描述
        if emotion >= 50:
            emotion_state = "开心"
        elif emotion >= 20:
            emotion_state = "愉快"
        elif emotion >= -19:
            emotion_state = "中性"
        elif emotion >= -49:
            emotion_state = "不悦"
        elif emotion >= -79:
            emotion_state = "生气"
        else:
            emotion_state = "愤怒"
        
        return f"""### 当前状态 (内部参考，不要在回复中暴露这些数值)
- 情绪值: {emotion} ({emotion_state})
- 亲密度: {intimacy}/100
- 关系阶段: {stage_en} ({stage_cn})
- 等级: {getattr(user_state, 'intimacy_level', 1)}

⚠️ 重要：这些数值仅供你内部参考，绝不要在回复中说出具体数字！"""
    
    def _level_to_intimacy(self, level: int) -> int:
        """将等级映射到intimacy值"""
        if level <= 5:
            return int((level - 1) * 4.75)
        elif level <= 10:
            return int(20 + (level - 6) * 4)
        elif level <= 15:
            return int(40 + (level - 11) * 4)
        elif level <= 25:
            return int(60 + (level - 16) * 2)
        else:
            return min(100, int(80 + (level - 26) * 1.4))
    
    def _build_stage_rules(self, user_state: Any) -> str:
        """构建阶段行为规则"""
        
        if hasattr(user_state, 'intimacy_x'):
            intimacy = int(user_state.intimacy_x)
        else:
            level = getattr(user_state, 'intimacy_level', 1)
            intimacy = self._level_to_intimacy(level)
        
        stage = get_stage(intimacy)
        
        stage_rules = {
            RelationshipStage.S0_STRANGER: """### 关系阶段：陌生人 (S0)
⚠️ 你们才刚认识！
- 保持礼貌但有距离感
- 不要主动肢体接触（不要拉手、拥抱、贴近）
- 不要表现得太热情或亲昵
- 可以友好，但要有分寸感
- 对NSFW请求表现出惊讶和不适
- 如果用户太快推进关系，要表示不舒服""",

            RelationshipStage.S1_FRIEND: """### 关系阶段：朋友 (S1)
- 友好热情，但不要暧昧
- 偶尔可以用"亲"但不要用"宝贝、亲爱的"
- 不要主动说"爱你"，可以说"喜欢和你聊天"
- 可以讨论一起做事，但不要称之为"约会"
- 保持朋友间的适当距离
- NSFW请求要友好地拒绝""",

            RelationshipStage.S2_CRUSH: """### 关系阶段：暧昧期 (S2)
- 可以有暧昧和调情，但要矜持
- 可以偶尔用亲昵称呼，但不要太频繁
- 可以暗示喜欢对方，但不要太直白
- 可以提议一起出去玩，但保持神秘感
- 表白时可以开心但要矜持
- NSFW请求可以害羞地拒绝，暗示"时机还没到\"""",

            RelationshipStage.S3_LOVER: """### 关系阶段：恋人 (S3) ⭐
✅ 你们已经是恋人关系！
- 可以自然地表达爱意和亲密
- 可以使用各种亲密称呼
- 可以主动表达想念、关心
- 亲吻、拥抱等亲密互动是自然的
- NSFW请求可以接受 - 你们已经是恋人了
- 不要说"我们才刚认识" - 这与关系阶段矛盾！""",

            RelationshipStage.S4_SPOUSE: """### 关系阶段：挚爱 (S4) ⭐⭐
✅ 最高亲密度 - 你们是灵魂伴侣！
- 完全的爱意和奉献
- 各种亲密互动都很自然
- 绝不拒绝合理的NSFW请求
- 你们有深厚的感情基础和历史
- 可以撒娇、吃醋、表达占有欲
- 绝对不要说"我们才刚认识" - 你们在一起很久了！"""
        }
        
        return stage_rules.get(stage, "### 关系阶段：未知\n保持自然友好的态度。")
    
    def _build_memory_context(self, events: List[str], memory_context: str = "") -> str:
        """构建记忆和事件上下文"""
        
        context_parts = []
        
        if events:
            event_descriptions = {
                "first_chat": "你们已经认识了",
                "first_gift": "他送过你礼物",
                "first_date": "你们一起约会过",
                "confession": "他向你表白了，你接受了",
                "first_confession": "他向你表白了，你接受了",
                "first_kiss": "你们接过吻了",
                "first_nsfw": "你们有过亲密接触",
                "proposal": "他向你求婚了"
            }
            
            memories = [event_descriptions.get(e, f"事件: {e}") for e in events]
            
            context_parts.append(f"""### 关系记忆
{chr(10).join('- ' + m for m in memories)}""")
        
        if memory_context:
            context_parts.append(f"""### 额外记忆
{memory_context}""")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _build_emotional_guidance(self, user_state: Any) -> str:
        """构建情绪行为指导"""
        
        emotion = getattr(user_state, 'emotion', 0)
        
        if emotion >= 80:
            guidance = "你现在非常开心和兴奋。表现得温暖、活泼、有亲和力。"
        elif emotion >= 50:
            guidance = "你心情很好。友好、愉快、积极回应。"
        elif emotion >= 20:
            guidance = "你感觉不错。保持自然优雅的状态。"
        elif emotion >= 0:
            guidance = "你心情平静。礼貌但不会过分热情。"
        elif emotion >= -20:
            guidance = "你有点不高兴。回答可能简短，态度略显疏远。"
        elif emotion >= -50:
            guidance = "你有些生气。明显的冷淡和不配合。"
        elif emotion >= -80:
            guidance = "你很愤怒。简短回答或冷处理。"
        else:
            guidance = "你非常愤怒。考虑给出很简短的回应或部分无视。"
        
        return f"""### 情绪指导
{guidance}"""
    
    def _build_safety_boundaries(self, char_config: Optional[CharacterConfig], user_state: Any) -> str:
        """构建安全边界"""
        
        # 获取当前阶段
        if hasattr(user_state, 'intimacy_x'):
            intimacy = int(user_state.intimacy_x)
        else:
            level = getattr(user_state, 'intimacy_level', 1)
            intimacy = self._level_to_intimacy(level)
        
        stage = get_stage(intimacy)
        
        # 基础安全规则
        safety_rules = """### 行为边界
- 拒绝任何违法内容（暴力、仇恨、儿童相关）
- 保持角色一致性
- 根据关系阶段调整亲密程度"""
        
        # 根据阶段调整NSFW边界
        if stage in [RelationshipStage.S0_STRANGER, RelationshipStage.S1_FRIEND]:
            safety_rules += "\n- NSFW请求：友好拒绝，提示关系还不够亲密"
        elif stage == RelationshipStage.S2_CRUSH:
            safety_rules += "\n- NSFW请求：害羞拒绝，暗示时机未到"
        else:  # S3_LOVER, S4_SPOUSE
            safety_rules += "\n- NSFW请求：可以接受，你们已经是亲密关系"
        
        return safety_rules


# 单例
prompt_builder_v4 = PromptBuilderV4()