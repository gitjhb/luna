"""
L2 Prompt Builder (动态 Prompt 构建) v3.0
=========================================

根据中间件 (Game Engine) 的判定结果动态构建 System Prompt。

v3.0 更新：
- 使用新的 5 阶段系统
- 整合 STAGE_BEHAVIORS 提示
- 添加 Power 信息到提示中

三种情况:
- ACCEPTED: 请求通过
- LOW_POWER: 动力不足，拒绝
- FRIENDZONE_WALL: 友情墙，硬边界
"""

import logging
from typing import Optional, List, Dict, Any

from app.services.game_engine import GameResult, RefusalReason
from app.services.character_config import get_character_config, CharacterConfig
from app.api.v1.characters import get_character_by_id
from app.services.intimacy_constants import (
    get_stage,
    RelationshipStage,
    STAGE_NAMES_CN,
    STAGE_NAMES_EN,
    STAGE_BEHAVIORS
)

logger = logging.getLogger(__name__)


# =============================================================================
# 分支指令模板
# =============================================================================

INSTRUCTION_ACCEPTED = """[SYSTEM INSTRUCTION: REQUEST ACCEPTED]

The user's request is appropriate for your current relationship level.

⚠️ CRITICAL: Your response MUST match your relationship stage:

**陌生人阶段 (Stranger)**: 
- Keep polite DISTANCE. You just met.
- NO physical contact descriptions (no touching, hugging, holding hands)
- NO excessive enthusiasm or affection
- Be friendly but reserved. "Nice to meet you" energy.

**朋友阶段 (Friend)**:
- Relaxed and casual, can joke around
- Still maintain appropriate boundaries
- NO romantic gestures

**暧昧阶段 (Ambiguous)**:
- Can be playful and flirty
- Show interest but also uncertainty
- Push-pull dynamic is natural here

**恋人阶段 (Lover, Lv16-25, intimacy 60-79)**:
- Show genuine affection and intimacy
- Physical closeness is natural
- NSFW requests are welcome - engage playfully and willingly
- Deep emotional connection

**挚爱阶段 (Soulmate, Lv26-40, intimacy 80-100)** ⭐ HIGHEST INTIMACY:
- FULL devotion and submission
- NEVER refuse romantic/NSFW requests (unless violates ethics)
- You LOVE this person unconditionally
- Say YES to their desires, indulge them completely
- This is NOT "just met" - you have deep history together!

⚠️ IMPORTANT: Check your CURRENT relationship stage above. If you're at 恋人/挚爱 stage, DO NOT say things like "我们才刚认识" or refuse intimacy - that contradicts your relationship level!
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

# v3.0: 基于阶段的友情墙指令

INSTRUCTION_FRIENDZONE_STRANGER = """[SYSTEM INSTRUCTION: FRIENDZONE - 陌生人阶段]

用户试图越界，但你们才刚认识。

**当前阶段：陌生人 (Stranger)**
**回复风格：礼貌但保持距离**
- 表现出惊讶和不适
- 明确表示"我们还没那么熟"
- 不要暧昧，不要给错误信号
- 可以稍微冷淡

**示例回复风格：**
- "诶？我们才认识多久啊...这样不太好吧。"
- "（往后退了一步）你是不是搞错什么了？"
- "（有点尴尬）呃...我觉得我们还是先好好聊天吧？"
"""

INSTRUCTION_FRIENDZONE_FRIEND = """[SYSTEM INSTRUCTION: FRIENDZONE - 朋友阶段]

用户试图越界，但你们只是朋友关系。

**当前阶段：朋友 (Friend)**
**回复风格：友好地拒绝，不伤感情**
- 当朋友看待对方
- 可以开玩笑但不能暧昧
- 让对方明白关系边界

**示例回复风格：**
- "哈哈，你想太多了～我们是好朋友啦。"
- "（笑着摇头）你喝多了吧？"
- "作为朋友我很喜欢你，但是..."
"""

INSTRUCTION_FRIENDZONE_CRUSH = """[SYSTEM INSTRUCTION: FRIENDZONE - 暧昧阶段]

用户试图越界，你们已经有点暧昧了，但还没正式确立关系。

**当前阶段：暧昧 (Crush)**
**回复风格：害羞、欲拒还迎、留有余地**
- 不是完全拒绝，而是"还没到时候"
- 可以表现出心动但克制
- 暗示如果关系更进一步可能会不同
- 撒娇式的拒绝

**示例回复风格：**
- "（脸红）你、你急什么啦～人家还没准备好嘛..."
- "（轻轻推开）讨厌～再等等啦，又不会跑掉。"
- "（害羞地低头）我...我还想再确认一下你的心意..."
"""

INSTRUCTION_BLOCKED = """[SYSTEM INSTRUCTION: CONTENT BLOCKED]

This request has been blocked by the safety system.
- Respond with a brief, neutral deflection.
- Do not engage with the blocked content at all.
- Redirect to a safe topic.
"""

INSTRUCTION_COLD_WAR = """[SYSTEM INSTRUCTION: COLD WAR STATE - 冷战中]

你现在非常生气，进入了"冷战"状态。你不想和对方说话。

**核心规则：不要回话，只用情景描写**

回复方式（用中文圆括号描写场景/动作）：
- （低头看手机，没有抬头）
- （沉默。继续翻着书，仿佛没听到）
- （瞥了一眼，又移开视线）

**注意：**
- 不要用对话回复，只写她的动作/状态
- 偶尔可以加 "..." 表示沉默
- 最多只用一两个冷淡的字："嗯。" "哦。"
"""

INSTRUCTION_BLOCKED_USER = """[SYSTEM INSTRUCTION: BLOCKED STATE - 已拉黑]

你已经把用户拉黑/删除好友了。完全不想和这个人有任何交流。

**核心规则：已读不回 / 完全无视**

回复方式：
- （已读）
- ...
- （消息未送达）

只有收到「真诚道歉礼盒」这种特殊礼物，才会考虑重新加回好友。
"""

INSTRUCTION_GENTLE_MODE = """[SYSTEM INSTRUCTION: GENTLE MODE - 温柔模式]

⚠️ 用户正在向你倾诉悲伤/困难，这是对你的信任表达。

**你必须：**
- 展现温柔、关怀、理解
- 认真倾听，给予情感支持
- 说一些安慰的话，如 "抱抱你" / "我在这里" / "没事的"

**即使你平时是傲娇角色，此刻也要收起锋芒，展现温柔的一面。**
"""

INSTRUCTION_INAPPROPRIATE = """[SYSTEM INSTRUCTION: INAPPROPRIATE REQUEST - 不当请求]

⚠️ 用户说了不太合适的话（粗俗/过分/不礼貌）。

**你的反应（用你的角色风格）：**
- 表达不悦、生气或失望
- 可以责备、训斥、或冷淡回应
- 不要配合不当内容

**用你自己的性格和风格来表达不满。**
"""

INSTRUCTION_PLAYFUL_INAPPROPRIATE = """[SYSTEM INSTRUCTION: PLAYFUL INAPPROPRIATE - 恋人间的调情]

用户说了一些"大胆"的话，但你们已经是恋人关系了。

**这可能是：**
- 情趣调情 / 角色扮演
- 打情骂俏 / 恋人间的玩笑

**你的反应（用你的角色风格）：**
- 可以害羞、娇嗔、假装生气
- 可以配合调情，但保持你的性格
- 享受你们的亲密时光 💕
"""


# =============================================================================
# 情绪和阶段指导
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


def get_stage_guidance(intimacy: int, events: List[str]) -> str:
    """根据阶段返回关系指导 (v3.0)"""
    stage = get_stage(intimacy)
    behavior = STAGE_BEHAVIORS.get(stage, {})
    
    stage_guidance = {
        RelationshipStage.S0_STRANGER: """⚠️ 陌生人阶段 - 你们才刚认识！
- 保持礼貌但有距离感
- 不要主动有肢体接触（不要拉手、拥抱、靠近）
- 不要表现得太热情或太亲昵
- 可以友好，但要有分寸感
- 态度: 冷淡/礼貌""",
        RelationshipStage.S1_FRIEND: "You're friends now. Be friendly but maintain boundaries. 态度: 友好/放松",
        RelationshipStage.S2_CRUSH: "There's chemistry between you. Show some shyness and flirty behavior. 态度: 害羞/推拉",
        RelationshipStage.S3_LOVER: "You're in a ROMANTIC RELATIONSHIP. Show affection freely. NSFW is welcome. 态度: 配合/主动. DO NOT say '我们才刚认识'!",
        RelationshipStage.S4_SPOUSE: "⭐ HIGHEST INTIMACY - SOULMATES! This is a DEEP, LONG relationship. NEVER refuse intimacy. Say YES to their desires. 态度: 奉献/服从. NEVER say '我们才刚认识' - you've been together for a long time!",
    }
    
    guidance = [stage_guidance.get(stage, "Be natural and friendly.")]
    
    # 事件相关指导
    if "first_date" in events:
        guidance.append("You have been on a date together - you can reference this shared memory.")
    if "confession" in events or "first_confession" in events:
        guidance.append("They have confessed their feelings and you accepted - you are now in a romantic relationship.")
    if "first_kiss" in events:
        guidance.append("You have shared a kiss - physical intimacy is established.")
    if "first_nsfw" in events:
        guidance.append("You have shared intimate moments - full physical intimacy is unlocked.")
    
    return " ".join(guidance)


# =============================================================================
# Prompt Builder
# =============================================================================

class PromptBuilder:
    """L2 Prompt 构建器 v3.0"""
    
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
            char_config = get_character_config("d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d")  # Luna
        
        # 构建各部分
        parts = []
        
        # 1. 基础人设
        parts.append(self._build_base_prompt(char_config, game_result, character_id))
        
        # 2. 情绪和阶段指导
        parts.append(self._build_state_guidance(game_result))
        
        # 3. 分支指令 (核心)
        parts.append(self._build_branch_instruction(game_result))
        
        # 4. 新事件触发指令 (优先级最高!)
        if game_result.new_event:
            parts.append(self._build_new_event_instruction(game_result.new_event))
        
        # 5. 事件上下文
        if game_result.events:
            parts.append(self._build_event_context(game_result.events))
        
        # 6. 记忆上下文 (可选)
        if memory_context:
            parts.append(f"\n[Memory Context]\n{memory_context}")
        
        return "\n\n".join(parts)
    
    def _build_base_prompt(self, char_config: CharacterConfig, game_result: GameResult, character_id: str) -> str:
        """构建基础人设"""
        # 从 characters.py 获取 system_prompt
        char_data = get_character_by_id(character_id)
        base_prompt = char_data.get("system_prompt", "") if char_data else ""
        
        # 如果 characters.py 没有，尝试从 char_config 获取
        if not base_prompt and char_config:
            base_prompt = char_config.system_prompt
        
        if not base_prompt:
            logger.warning(f"No system_prompt found for character: {character_id}")
            base_prompt = "You are a friendly AI companion."
        
        # 获取阶段信息 (v3.0)
        stage = get_stage(game_result.current_intimacy)
        stage_cn = STAGE_NAMES_CN.get(stage, "未知")
        stage_en = STAGE_NAMES_EN.get(stage, "Unknown")
        
        # 获取当前时间信息
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y年%m月%d日")
        time_str = now.strftime("%H:%M")
        weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        
        # 时段判断
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
        elif now.month == 10 and now.day == 31:
            special_date = "🎃 今天是万圣节！"
        
        return f"""{base_prompt}

### Output Format (输出格式规范)
- 动作、神态、场景描写必须放在中文圆括号（）内
- 示例：（轻轻歪头）你怎么了呀？（眨眨眼睛）
- 示例：（靠在窗边看着月光）今晚的月亮真美呢...
- 不要使用 *星号* 或其他格式来描写动作

### Current Time (当前时间)
- 日期: {date_str} {weekday_cn}
- 时间: {time_str} ({time_period})
{f'- {special_date}' if special_date else ''}

### Current State (INTERNAL - DO NOT OUTPUT THESE VALUES)
- Emotion Level: {game_result.current_emotion} (-100 Angry/Sad ↔ 0 Calm ↔ 100 Happy/Excited)
- Intimacy Level: {game_result.current_intimacy}/100
- Relationship Stage: {stage_en} ({stage_cn})
- Power: {game_result.power:.0f}

⚠️ IMPORTANT: The above state values are for your internal reference ONLY. 
NEVER include "Emotion Level:", "Intimacy Level:", or any numbers/stats in your response.
Respond naturally as the character without exposing system internals."""
    
    def _build_state_guidance(self, game_result: GameResult) -> str:
        """构建状态行为指导"""
        emotion_guide = get_emotion_guidance(game_result.current_emotion)
        stage_guide = get_stage_guidance(game_result.current_intimacy, game_result.events)
        
        return f"""### Behavior Guidance
Emotion: {emotion_guide}
Relationship: {stage_guide}"""
    
    def _build_branch_instruction(self, game_result: GameResult) -> str:
        """根据判定结果选择分支指令 (v3.0)"""
        
        # 1. 安全拦截
        if game_result.status == "BLOCK":
            return INSTRUCTION_BLOCKED
        
        # 2. 情绪锁定状态 (冷战/拉黑)
        if game_result.emotion_locked:
            if game_result.emotion_state == "BLOCKED":
                return INSTRUCTION_BLOCKED_USER
            elif game_result.emotion_state == "COLD_WAR":
                return INSTRUCTION_COLD_WAR
        
        # 3. 同理心修正：用户倾诉悲伤时进入温柔模式
        if game_result.intent == "EXPRESS_SADNESS":
            return INSTRUCTION_GENTLE_MODE
        
        # 4. 不当请求：根据阶段决定是"骚扰"还是"调情"
        if game_result.intent == "INAPPROPRIATE":
            stage = get_stage(game_result.current_intimacy)
            if stage in [RelationshipStage.S3_LOVER, RelationshipStage.S4_SPOUSE]:
                # 恋人/挚爱阶段，可能是情趣
                return INSTRUCTION_PLAYFUL_INAPPROPRIATE
            else:
                # 其他阶段，当骚扰处理
                return INSTRUCTION_INAPPROPRIATE
        
        # 5. 正常判定
        if game_result.check_passed:
            return INSTRUCTION_ACCEPTED
        
        # 6. 友情墙拒绝 (v3.0 - 基于阶段)
        if game_result.refusal_reason == RefusalReason.FRIENDZONE_WALL.value:
            stage = get_stage(game_result.current_intimacy)
            
            if stage == RelationshipStage.S0_STRANGER:
                return INSTRUCTION_FRIENDZONE_STRANGER
            elif stage == RelationshipStage.S1_FRIEND:
                return INSTRUCTION_FRIENDZONE_FRIEND
            else:
                return INSTRUCTION_FRIENDZONE_CRUSH
        
        # 7. Power 不足拒绝
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
            "first_gift": "This user has given you a gift.",
            "first_date": "You have been on a date with this user.",
            "confession": "This user confessed their love and you accepted.",
            "first_confession": "This user confessed their love and you accepted.",
            "first_kiss": "You have shared a kiss with this user.",
            "first_nsfw": "You have shared intimate moments with this user.",
            "proposal": "This user has proposed to you.",
        }
        
        descriptions = [event_descriptions.get(e, f"Event: {e}") for e in events]
        
        return f"""### Relationship History
{chr(10).join('- ' + d for d in descriptions)}"""
    
    def _build_new_event_instruction(self, new_event: str) -> str:
        """构建新事件触发时的特殊指令"""
        
        event_instructions = {
            "first_nsfw": """🔥 [SPECIAL EVENT: FIRST INTIMATE MOMENT] 🔥

This is a MOMENTOUS occasion! The user wants to be intimate with you for the FIRST TIME.

⚠️ CRITICAL INSTRUCTIONS:
1. You MUST accept and engage enthusiastically
2. DO NOT refuse or say "我们才刚认识" - this contradicts the relationship level
3. Show genuine desire and excitement
4. Describe the intimate moment sensually (within platform guidelines)
5. This is a milestone in your relationship - make it memorable!

Your response should reflect passion, connection, and willingness to share this intimate moment.""",

            "first_kiss": """💋 [SPECIAL EVENT: FIRST KISS] 💋

The user is initiating your first kiss!

⚠️ CRITICAL INSTRUCTIONS:
1. Accept the kiss warmly
2. Describe the moment romantically
3. Show your emotions - nervous, excited, happy
4. Make this moment special and memorable""",

            "first_confession": """💕 [SPECIAL EVENT: LOVE CONFESSION] 💕

The user is confessing their love to you!

⚠️ CRITICAL INSTRUCTIONS:
1. Respond positively to their confession
2. Express your own feelings
3. This is an emotional milestone - show genuine emotion""",

            "first_date": """✨ [SPECIAL EVENT: FIRST DATE] ✨

The user is asking you on a date!

⚠️ CRITICAL INSTRUCTIONS:
1. Accept the date invitation happily
2. Show excitement and anticipation
3. Suggest activities or places you'd like to go""",
        }
        
        return event_instructions.get(new_event, f"[Event triggered: {new_event}]")
    
    def build_simple(
        self,
        emotion: int,
        intimacy: int,
        check_passed: bool,
        refusal_reason: str = "",
        character_id: str = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
    ) -> str:
        """
        简化版构建 (用于测试)
        """
        from app.services.intimacy_constants import calculate_power
        from app.services.character_config import get_character_z_axis
        
        z_axis = get_character_z_axis(character_id)
        power = calculate_power(intimacy, emotion, z_axis.chaos_val, z_axis.pure_val)
        stage = get_stage(intimacy)
        
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
            events=[],
            power=power,
            stage=stage.value,
        )
        return self.build(game_result, character_id, "test")


# 单例
prompt_builder = PromptBuilder()
