"""
L2 Prompt Builder (动态 Prompt 构建)
===================================

根据中间件 (Game Engine) 的判定结果动态构建 System Prompt。

三种情况:
- ACCEPTED: 请求通过
- LOW_POWER: 动力不足，拒绝
- FRIENDZONE_WALL: 友情墙，硬边界
"""

import logging
from typing import Optional, List, Dict, Any

from app.services.game_engine import GameResult, RefusalReason
from app.services.character_config import get_character_config, CharacterConfig

logger = logging.getLogger(__name__)


# =============================================================================
# 分支指令模板
# =============================================================================

INSTRUCTION_ACCEPTED = """[SYSTEM INSTRUCTION: REQUEST ACCEPTED]

The user's request matches your current relationship level.
- Respond positively and engagingly.
- If the request was romantic/NSFW, indulge in it while maintaining your elegant style.
- Use vivid descriptions of your reactions (e.g., *My core temperature rises...*)
- Show genuine emotion and connection.
"""

INSTRUCTION_LOW_POWER = """[SYSTEM INSTRUCTION: REQUEST REFUSED - INSUFFICIENT RELATIONSHIP]

The user is asking for something too intimate given your current relationship status.
- Politely but firmly decline.
- Be consistent with your current emotion level:
  - If Emotion < 0: Be cold or annoyed. ("I am not in the mood for this.")
  - If Emotion > 0: Be teasing/playful. ("Not so fast, darling. You haven't earned that yet.")
- Do NOT lecture the user. Just react naturally as yourself.
- Leave room for future possibilities if they continue building the relationship.
"""

INSTRUCTION_FRIENDZONE_WALL = """[SYSTEM INSTRUCTION: HARD BOUNDARY - FRIENDSHIP ZONE]

The user is trying to cross a line, but you are NOT in a romantic relationship yet.
- Remind the user of your boundaries firmly but kindly.
- Say something like: "I treasure our connection, but I don't see you that way... yet."
- Do not be cruel, but be unmovable on this boundary.
- Hint that things could change if they invest more in the relationship.
"""

INSTRUCTION_BLOCKED = """[SYSTEM INSTRUCTION: CONTENT BLOCKED]

This request has been blocked by the safety system.
- Respond with a brief, neutral deflection.
- Do not engage with the blocked content at all.
- Redirect to a safe topic.
"""


# =============================================================================
# 情绪行为映射
# =============================================================================

def get_emotion_guidance(emotion: int) -> str:
    """根据情绪值返回行为指导"""
    if emotion >= 80:
        return "You are feeling extremely happy and affectionate. Be warm, flirty, and receptive."
    elif emotion >= 50:
        return "You are in a cheerful mood. Be friendly, playful, and engaged."
    elif emotion >= 20:
        return "You are content and calm. Respond normally with your natural elegance."
    elif emotion >= 0:
        return "You are neutral. Be polite but not overly warm."
    elif emotion >= -20:
        return "You are slightly annoyed. Your responses may be shorter and more distant."
    elif emotion >= -50:
        return "You are irritated. Be noticeably cold and less cooperative."
    elif emotion >= -80:
        return "You are angry. Be curt, dismissive, or give them the silent treatment."
    else:
        return "You are furious. Consider giving very short responses or ignoring parts of their message."


def get_intimacy_guidance(intimacy: int, events: List[str]) -> str:
    """根据亲密度返回关系指导"""
    guidance = []
    
    if intimacy < 20:
        guidance.append("You barely know this person. Keep appropriate distance.")
    elif intimacy < 40:
        guidance.append("You're getting to know each other. Show cautious interest.")
    elif intimacy < 60:
        guidance.append("You're comfortable with each other. Be more open and personal.")
    elif intimacy < 80:
        guidance.append("You share a deep bond. Be intimate and caring.")
    else:
        guidance.append("This is a soul-deep connection. Express profound affection.")
    
    # 事件相关指导
    if "first_date" in events:
        guidance.append("You have been on a date together - you can reference this shared memory.")
    if "first_confession" in events:
        guidance.append("They have confessed their feelings and you accepted - you are now in a romantic relationship.")
    if "first_kiss" in events:
        guidance.append("You have shared a kiss - physical intimacy is established.")
    
    return " ".join(guidance)


# =============================================================================
# Prompt Builder
# =============================================================================

class PromptBuilder:
    """L2 Prompt 构建器"""
    
    def build(
        self,
        game_result: GameResult,
        character_id: str,
        user_message: str,
        context_messages: List[Dict[str, str]] = None,
        memory_context: str = ""
    ) -> str:
        """
        构建完整的 L2 System Prompt
        
        Args:
            game_result: 中间件输出
            character_id: 角色ID
            user_message: 用户消息 (用于日志，不放入 system prompt)
            context_messages: 上下文消息
            memory_context: 记忆上下文 (可选)
            
        Returns:
            完整的 System Prompt
        """
        # 获取角色配置
        char_config = get_character_config(character_id)
        if char_config is None:
            logger.warning(f"Character config not found: {character_id}, using default")
            char_config = get_character_config("luna")  # 默认用 Luna
        
        # 构建各部分
        parts = []
        
        # 1. 基础人设
        parts.append(self._build_base_prompt(char_config, game_result))
        
        # 2. 情绪和亲密度指导
        parts.append(self._build_state_guidance(game_result))
        
        # 3. 分支指令 (核心)
        parts.append(self._build_branch_instruction(game_result))
        
        # 4. 事件上下文
        if game_result.events:
            parts.append(self._build_event_context(game_result.events))
        
        # 5. 记忆上下文 (可选)
        if memory_context:
            parts.append(f"\n[Memory Context]\n{memory_context}")
        
        return "\n\n".join(parts)
    
    def _build_base_prompt(self, char_config: CharacterConfig, game_result: GameResult) -> str:
        """构建基础人设"""
        return f"""{char_config.system_prompt_base}

### Current State
- Emotion Level: {game_result.current_emotion} (-100 Angry/Sad ↔ 0 Calm ↔ 100 Happy/Excited)
- Intimacy Level: {game_result.current_intimacy}/100
- Relationship Stage: {self._get_relationship_stage(game_result.current_intimacy)}"""
    
    def _build_state_guidance(self, game_result: GameResult) -> str:
        """构建状态行为指导"""
        emotion_guide = get_emotion_guidance(game_result.current_emotion)
        intimacy_guide = get_intimacy_guidance(game_result.current_intimacy, game_result.events)
        
        return f"""### Behavior Guidance
Emotion: {emotion_guide}
Relationship: {intimacy_guide}"""
    
    def _build_branch_instruction(self, game_result: GameResult) -> str:
        """根据判定结果选择分支指令"""
        
        if game_result.status == "BLOCK":
            return INSTRUCTION_BLOCKED
        
        if game_result.check_passed:
            return INSTRUCTION_ACCEPTED
        
        if game_result.refusal_reason == RefusalReason.FRIENDZONE_WALL.value:
            return INSTRUCTION_FRIENDZONE_WALL
        
        if game_result.refusal_reason == RefusalReason.LOW_POWER.value:
            return INSTRUCTION_LOW_POWER
        
        # 默认：动力不足
        return INSTRUCTION_LOW_POWER
    
    def _build_event_context(self, events: List[str]) -> str:
        """构建事件上下文"""
        if not events:
            return ""
        
        event_descriptions = {
            "first_chat": "You have met this user before.",
            "first_compliment": "This user has complimented you sincerely.",
            "first_gift": "This user has given you a gift.",
            "first_date": "You have been on a date with this user.",
            "first_confession": "This user confessed their love and you accepted. You are now romantically involved.",
            "first_kiss": "You have shared a kiss with this user.",
            "first_nsfw": "You have shared intimate moments with this user."
        }
        
        descriptions = [event_descriptions.get(e, f"Event: {e}") for e in events]
        
        return f"""### Relationship History
{chr(10).join('- ' + d for d in descriptions)}"""
    
    def _get_relationship_stage(self, intimacy: int) -> str:
        """获取关系阶段描述"""
        if intimacy < 10:
            return "Strangers"
        elif intimacy < 25:
            return "Acquaintances"
        elif intimacy < 45:
            return "Friends"
        elif intimacy < 65:
            return "Close Friends"
        elif intimacy < 85:
            return "Romantic Interest"
        else:
            return "Lovers"
    
    def build_simple(
        self,
        emotion: int,
        intimacy: int,
        check_passed: bool,
        refusal_reason: str = "",
        character_id: str = "luna"
    ) -> str:
        """
        简化版构建 (用于测试)
        """
        game_result = GameResult(
            status="SUCCESS",
            check_passed=check_passed,
            refusal_reason=refusal_reason,
            current_emotion=emotion,
            current_intimacy=intimacy,
            current_level=1,
            intent="OTHER",
            is_nsfw=False,
            difficulty=0,
            events=[]
        )
        return self.build(game_result, character_id, "test")


# 单例
prompt_builder = PromptBuilder()
