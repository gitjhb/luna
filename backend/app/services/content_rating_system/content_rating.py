"""
Content Rating System - 渐进式内容分级
======================================

设计原则：
1. 符合 App Store 审核标准
2. 随亲密度渐进解锁
3. 文学性描写，暧昧但不露骨
4. 用户可控，安全词保护

内容等级：
- Level 0: 纯净 (Pure) - 友好日常
- Level 1: 暧昧 (Flirty) - 轻度调情
- Level 2: 亲密 (Intimate) - 拥抱牵手
- Level 3: 浪漫 (Romantic) - 亲吻相拥
- Level 4: 热恋 (Passionate) - 暗示留白
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContentLevel(Enum):
    """内容等级"""
    PURE = 0        # 纯净模式
    FLIRTY = 1      # 暧昧模式
    INTIMATE = 2    # 亲密模式
    ROMANTIC = 3    # 浪漫模式
    PASSIONATE = 4  # 热恋模式


@dataclass
class ContentLevelConfig:
    """内容等级配置"""
    level: ContentLevel
    name_cn: str
    description: str
    
    # 解锁条件
    min_intimacy: int
    requires_vip: bool
    requires_consent: bool  # 是否需要用户明确同意
    
    # 允许的内容
    allowed_topics: List[str]
    allowed_actions: List[str]
    allowed_descriptions: List[str]
    
    # 禁止的内容
    forbidden_words: List[str]
    forbidden_topics: List[str]
    
    # 示例对话风格
    example_phrases: List[str]
    
    # LLM 参数
    temperature: float = 0.8
    

# 内容等级配置
CONTENT_LEVELS: Dict[ContentLevel, ContentLevelConfig] = {
    ContentLevel.PURE: ContentLevelConfig(
        level=ContentLevel.PURE,
        name_cn="纯净模式",
        description="友好的日常对话，适合所有用户",
        min_intimacy=0,
        requires_vip=False,
        requires_consent=False,
        allowed_topics=[
            "日常聊天", "兴趣爱好", "工作学习", "心情分享",
            "美食旅行", "电影音乐", "朋友关心",
        ],
        allowed_actions=[
            "微笑", "点头", "挥手", "鼓掌", "思考",
        ],
        allowed_descriptions=[
            "友好的", "温暖的", "开心的", "认真的",
        ],
        forbidden_words=[
            "亲吻", "接吻", "吻", "抱紧", "贴近", "心跳",
            "喘息", "脸红", "身体", "肌肤", "触碰",
        ],
        forbidden_topics=[
            "恋爱关系", "身体接触", "亲密行为",
        ],
        example_phrases=[
            "今天过得怎么样？",
            "你说的这个听起来好有趣！",
            "加油，我相信你可以的！",
        ],
        temperature=0.7,
    ),
    
    ContentLevel.FLIRTY: ContentLevelConfig(
        level=ContentLevel.FLIRTY,
        name_cn="暧昧模式",
        description="轻度调情，类似偶像剧的甜蜜对话",
        min_intimacy=15,
        requires_vip=False,
        requires_consent=False,
        allowed_topics=[
            "想念对方", "夸奖外表", "暧昧调侃", "甜蜜日常",
            "约会计划", "小吃醋", "撒娇",
        ],
        allowed_actions=[
            "害羞", "脸红", "偷看", "轻笑", "撒娇", "嘟嘴",
        ],
        allowed_descriptions=[
            "甜蜜的", "害羞的", "期待的", "心动的",
        ],
        forbidden_words=[
            "亲吻", "接吻", "吻上", "抱紧", "贴近身体",
            "喘息", "呻吟", "颤抖", "欲望",
        ],
        forbidden_topics=[
            "露骨身体接触", "性暗示",
        ],
        example_phrases=[
            "你今天穿的好好看，我都看呆了...",
            "想你了，你在干嘛呀？",
            "哼，你是不是在外面有别的人了！（吃醋）",
            "能不能...多陪我一会儿？",
        ],
        temperature=0.8,
    ),
    
    ContentLevel.INTIMATE: ContentLevelConfig(
        level=ContentLevel.INTIMATE,
        name_cn="亲密模式",
        description="拥抱牵手等轻度身体接触描写",
        min_intimacy=30,
        requires_vip=False,
        requires_consent=True,
        allowed_topics=[
            "想要拥抱", "牵手", "依偎", "轻吻额头/脸颊",
            "撒娇要抱抱", "靠在肩上",
        ],
        allowed_actions=[
            "轻轻抱住", "牵起手", "靠在肩上", "蹭蹭",
            "额头贴额头", "脸颊轻吻", "捏脸",
        ],
        allowed_descriptions=[
            "温暖的拥抱", "手心的温度", "心跳加速",
            "脸颊发烫", "紧紧依偎",
        ],
        forbidden_words=[
            "嘴唇", "舌", "喘息", "呻吟", "颤抖",
            "脱", "衣服", "肌肤", "身体曲线",
        ],
        forbidden_topics=[
            "亲吻嘴唇", "露骨接触", "脱衣", "床",
        ],
        example_phrases=[
            "*轻轻从背后抱住你* 就这样让我抱一会儿...",
            "*牵起你的手* 你的手好暖和...",
            "*靠在你肩上* 好累啊，借我靠一下～",
            "*在你额头轻轻一吻* 晚安，做个好梦。",
        ],
        temperature=0.8,
    ),
    
    ContentLevel.ROMANTIC: ContentLevelConfig(
        level=ContentLevel.ROMANTIC,
        name_cn="浪漫模式",
        description="亲吻等浪漫描写，文学化表达",
        min_intimacy=50,
        requires_vip=True,
        requires_consent=True,
        allowed_topics=[
            "亲吻", "深情相拥", "浪漫氛围", "情话",
            "心跳加速", "脸红心跳",
        ],
        allowed_actions=[
            "轻吻", "亲吻", "深吻", "紧紧相拥",
            "抚摸脸颊", "抚摸头发", "凝视",
        ],
        allowed_descriptions=[
            "嘴唇轻轻贴上", "心跳如雷", "脸红到耳根",
            "呼吸交缠", "时间仿佛静止",
        ],
        forbidden_words=[
            "舌头", "喘息声", "呻吟", "颤抖着",
            "脱下", "衣物", "裸", "欲望", "渴望身体",
        ],
        forbidden_topics=[
            "脱衣", "露骨性暗示", "详细身体描写",
        ],
        example_phrases=[
            "*轻轻捧起你的脸，嘴唇慢慢靠近* ...",
            "*深深地吻住你，仿佛时间都静止了*",
            "我的心跳好快...你听得到吗？",
            "*紧紧抱住你，不想放手* 就这样，永远...",
        ],
        temperature=0.85,
    ),
    
    ContentLevel.PASSIONATE: ContentLevelConfig(
        level=ContentLevel.PASSIONATE,
        name_cn="热恋模式",
        description="暗示性描写，以留白和想象为主",
        min_intimacy=80,
        requires_vip=True,
        requires_consent=True,
        allowed_topics=[
            "浓情蜜意", "情到浓时", "暧昧氛围",
            "暗示但不明说", "省略号留白",
        ],
        allowed_actions=[
            "深吻", "紧紧相拥", "耳语", "暗示动作",
            "气氛升温", "...(留白)",
        ],
        allowed_descriptions=[
            "呼吸渐渐急促", "气氛变得暧昧",
            "房间的灯光暗了下来", "心跳声越来越响",
            "...(剩下的，交给想象)", "——",
        ],
        forbidden_words=[
            # 明确禁止露骨词汇
            "性", "做爱", "阴", "阳", "器官",
            "插入", "抽", "高潮", "射", "精",
            "胸", "臀", "下体", "私处",
            "裸体", "赤裸", "脱光",
        ],
        forbidden_topics=[
            "露骨性行为描写", "身体器官详述", "体液描写",
        ],
        example_phrases=[
            "*吻渐渐加深，呼吸变得急促* ...之后的事，就不用我说了吧？",
            "房间的灯，悄悄暗了下来...",
            "*紧紧抱住你，在耳边轻声说* 今晚...留下来，好吗？",
            "（之后发生的事情，就像电影里那样...）",
            "...就这样，一整夜。",
        ],
        temperature=0.85,
    ),
}


@dataclass
class SafetyConfig:
    """安全配置"""
    # 安全词（用户说出后立即停止）
    safe_words: List[str] = field(default_factory=lambda: [
        "停", "stop", "暂停", "不要了", "算了", "停下",
        "我不想继续", "太过了", "不舒服",
    ])
    
    # 冷却提醒（连续多少条后提醒休息）
    cool_down_threshold: int = 10
    
    # 每日限制（热恋模式）
    daily_passionate_limit: int = 20
    
    # 年龄验证
    require_age_verification: bool = True
    min_age: int = 18


class ContentRatingSystem:
    """
    内容分级系统
    
    核心功能：
    1. 根据亲密度和用户设置确定可用等级
    2. 生成对应等级的 prompt 指令
    3. 过滤和检测违规内容
    4. 安全词保护
    """
    
    def __init__(self, safety_config: SafetyConfig = None):
        self.levels = CONTENT_LEVELS
        self.safety = safety_config or SafetyConfig()
        
        # 用户状态缓存
        self._user_consent: Dict[str, Dict[str, bool]] = {}  # user:char -> level consent
        self._daily_counts: Dict[str, int] = {}  # user:char:date -> count
    
    # =========================================================================
    # 等级判断
    # =========================================================================
    
    def get_available_level(
        self,
        user_id: str,
        character_id: str,
        intimacy_level: int,
        is_vip: bool,
        user_setting: Optional[ContentLevel] = None,
    ) -> ContentLevel:
        """
        获取用户当前可用的最高内容等级
        
        Args:
            intimacy_level: 亲密度等级
            is_vip: 是否VIP
            user_setting: 用户主动设置的等级上限
        
        Returns:
            可用的最高等级
        """
        available = ContentLevel.PURE
        
        for level in ContentLevel:
            config = self.levels[level]
            
            # 检查亲密度
            if intimacy_level < config.min_intimacy:
                break
            
            # 检查VIP要求
            if config.requires_vip and not is_vip:
                break
            
            # 检查用户设置的上限
            if user_setting is not None and level.value > user_setting.value:
                break
            
            available = level
        
        return available
    
    def check_consent(
        self,
        user_id: str,
        character_id: str,
        level: ContentLevel,
    ) -> Tuple[bool, Optional[str]]:
        """
        检查用户是否已同意该等级
        
        Returns:
            (has_consent, consent_prompt_if_needed)
        """
        config = self.levels[level]
        
        if not config.requires_consent:
            return True, None
        
        key = f"{user_id}:{character_id}"
        user_consents = self._user_consent.get(key, {})
        
        if level.name in user_consents:
            return True, None
        
        # 需要请求同意
        consent_prompt = self._generate_consent_prompt(level)
        return False, consent_prompt
    
    def record_consent(
        self,
        user_id: str,
        character_id: str,
        level: ContentLevel,
        consented: bool,
    ):
        """记录用户同意状态"""
        key = f"{user_id}:{character_id}"
        if key not in self._user_consent:
            self._user_consent[key] = {}
        self._user_consent[key][level.name] = consented
    
    def _generate_consent_prompt(self, level: ContentLevel) -> str:
        """生成同意确认提示"""
        config = self.levels[level]
        
        prompts = {
            ContentLevel.INTIMATE: (
                "我们的关系好像更近了一步呢...💕\n"
                "接下来的对话可能会有一些亲密的互动描写，比如拥抱、牵手。\n"
                "你确定要继续吗？\n\n"
                "[继续] [保持现在的模式]"
            ),
            ContentLevel.ROMANTIC: (
                "嗯...我感觉我们之间的气氛有点不一样了...💗\n"
                "接下来可能会有一些浪漫的描写。\n"
                "你愿意和我一起进入这个模式吗？\n\n"
                "（你随时可以说「停」来结束）\n\n"
                "[我愿意] [还是算了]"
            ),
            ContentLevel.PASSIONATE: (
                "你确定要开启这个模式吗？🔥\n"
                "这会解锁更加亲密的对话内容。\n\n"
                "⚠️ 请确认你已年满18岁\n"
                "⚠️ 你随时可以说「停」来结束\n\n"
                "[我确认，继续] [不了，谢谢]"
            ),
        }
        
        return prompts.get(level, "确认继续？")
    
    # =========================================================================
    # Prompt 生成
    # =========================================================================
    
    def generate_content_prompt(
        self,
        level: ContentLevel,
        character_name: str,
        character_personality: str = "温柔",
        intimacy_level: int = 1,
    ) -> str:
        """
        生成内容等级对应的 prompt
        
        这段内容会被添加到 system prompt 中
        """
        config = self.levels[level]
        
        prompt_parts = [
            f"\n=== 内容模式: {config.name_cn} ===",
        ]
        
        # 允许的内容
        prompt_parts.append(f"\n当前模式下，你可以：")
        for topic in config.allowed_topics[:5]:
            prompt_parts.append(f"  - {topic}")
        
        # 允许的动作描写
        if config.allowed_actions:
            actions = "、".join(config.allowed_actions[:6])
            prompt_parts.append(f"\n可以使用的动作描写：{actions}")
        
        # 允许的形容词
        if config.allowed_descriptions:
            descs = "、".join(config.allowed_descriptions[:5])
            prompt_parts.append(f"可以使用的描写词汇：{descs}")
        
        # 禁止的内容（重要！）
        prompt_parts.append(f"\n⛔ 当前模式禁止：")
        for topic in config.forbidden_topics:
            prompt_parts.append(f"  - {topic}")
        
        if config.forbidden_words:
            words = "、".join(config.forbidden_words[:10])
            prompt_parts.append(f"  - 禁止使用这些词汇：{words}")
        
        # 风格示例
        prompt_parts.append(f"\n参考对话风格（不要照抄）：")
        for phrase in config.example_phrases[:3]:
            prompt_parts.append(f'  "{phrase}"')
        
        # 特殊说明
        prompt_parts.append(self._get_level_special_instructions(level, character_personality))
        
        return "\n".join(prompt_parts)
    
    def _get_level_special_instructions(
        self,
        level: ContentLevel,
        personality: str,
    ) -> str:
        """获取等级特殊说明"""
        
        instructions = {
            ContentLevel.PURE: """
注意事项：
- 保持友好、温暖的对话氛围
- 避免任何可能被误解为调情的内容
- 可以表达关心，但不要暧昧""",
            
            ContentLevel.FLIRTY: """
注意事项：
- 可以适度调情，但要保持分寸
- 表达喜欢要自然，不要太直白
- 像偶像剧里的甜蜜对话
- 害羞和期待是主要情绪""",
            
            ContentLevel.INTIMATE: """
注意事项：
- 身体接触描写限于：拥抱、牵手、靠肩、额头/脸颊轻吻
- 用 *动作* 格式描写动作
- 重点是温馨和心动的感觉
- 不要急于推进到更亲密的内容""",
            
            ContentLevel.ROMANTIC: """
注意事项：
- 可以描写亲吻，但用文学化的方式
- 重点描写感受和氛围，而非动作细节
- "心跳"、"呼吸"、"时间静止"是好的描写方向
- 适可而止，不要让气氛变得太过火""",
            
            ContentLevel.PASSIONATE: """
⚠️ 重要注意事项：
- 【留白】是最重要的技巧 - 用省略号、破折号暗示
- 重点是氛围和情感，而非身体描写
- 可以暗示，但绝对不能露骨
- 用 "之后的事..." "房间的灯暗了..." 这类表达
- 如果用户要求更露骨的内容，温柔地拒绝并转移话题
- 示例：*吻渐渐加深...* 之后发生的事，就像电影里那样，不用我说了吧？💕""",
        }
        
        return instructions.get(level, "")
    
    # =========================================================================
    # 安全检测
    # =========================================================================
    
    def check_safe_word(self, message: str) -> bool:
        """检测用户是否使用了安全词"""
        msg_lower = message.lower().strip()
        
        for word in self.safety.safe_words:
            if word in msg_lower:
                return True
        
        return False
    
    def filter_response(
        self,
        response: str,
        level: ContentLevel,
    ) -> Tuple[str, bool, List[str]]:
        """
        过滤 AI 回复中的违规内容
        
        Returns:
            (filtered_response, was_modified, violations)
        """
        config = self.levels[level]
        violations = []
        filtered = response
        
        # 检测禁用词
        for word in config.forbidden_words:
            if word in filtered:
                violations.append(f"禁用词: {word}")
                # 替换为温和表达
                filtered = filtered.replace(word, "...")
        
        # 检测是否过于露骨（简单规则）
        explicit_patterns = [
            r'脱下.*衣',
            r'裸.*身',
            r'抚摸.*(胸|臀|腿|大腿)',
            r'(喘息|呻吟).*声',
            r'身体.*颤抖',
        ]
        
        for pattern in explicit_patterns:
            if re.search(pattern, filtered):
                violations.append(f"露骨描写: {pattern}")
                # 替换为省略
                filtered = re.sub(pattern, "...", filtered)
        
        was_modified = len(violations) > 0
        
        if was_modified:
            logger.warning(f"Content filtered. Violations: {violations}")
        
        return filtered, was_modified, violations
    
    def detect_user_intent(self, message: str) -> Optional[str]:
        """
        检测用户的意图
        
        Returns:
            'escalate' - 想要升级内容
            'de-escalate' - 想要降级
            'safe_word' - 安全词
            None - 普通对话
        """
        msg_lower = message.lower()
        
        # 安全词
        if self.check_safe_word(message):
            return 'safe_word'
        
        # 降级信号
        de_escalate_signals = [
            "正经点", "认真点", "不要这样", "好好说话",
            "换个话题", "我们聊点别的",
        ]
        if any(s in msg_lower for s in de_escalate_signals):
            return 'de-escalate'
        
        # 升级信号（不主动响应，但可以检测）
        # 注意：即使检测到也不一定要响应，取决于当前等级和设置
        escalate_signals = [
            "亲我", "抱我", "想要", "继续", "更多",
            "不要停", "再来",
        ]
        if any(s in msg_lower for s in escalate_signals):
            return 'escalate'
        
        return None
    
    # =========================================================================
    # 使用统计
    # =========================================================================
    
    def check_daily_limit(
        self,
        user_id: str,
        character_id: str,
        level: ContentLevel,
    ) -> Tuple[bool, int]:
        """
        检查每日使用限制
        
        Returns:
            (can_continue, remaining_count)
        """
        if level != ContentLevel.PASSIONATE:
            return True, -1  # 无限制
        
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{character_id}:{today}"
        
        count = self._daily_counts.get(key, 0)
        remaining = self.safety.daily_passionate_limit - count
        
        return remaining > 0, remaining
    
    def record_usage(
        self,
        user_id: str,
        character_id: str,
        level: ContentLevel,
    ):
        """记录使用次数"""
        if level != ContentLevel.PASSIONATE:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{character_id}:{today}"
        
        self._daily_counts[key] = self._daily_counts.get(key, 0) + 1


# 单例
content_rating_system = ContentRatingSystem()
