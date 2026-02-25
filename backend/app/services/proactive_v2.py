"""
Proactive Messaging Service v2
==============================
借鉴 Mio 的智能主动消息系统，加入：
- 多语言支持 (en/zh)
- Engagement decay (用户不回就衰减)
- 时段 + 活动场景
- 上下文感知
- 亲密度驱动频率
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json

logger = logging.getLogger(__name__)

# =============================================================================
# 配置
# =============================================================================

class ProactiveMode(str, Enum):
    """发送模式 - 基于用户回复情况"""
    NORMAL = "normal"       # 正常发
    MISSING = "missing"     # 想你了
    WORRIED = "worried"     # 担心你
    GOODBYE = "goodbye"     # 找别人了
    SILENT = "silent"       # 不发了


class TimeSlot(str, Enum):
    """时间段"""
    MORNING = "morning"         # 7-9点
    NOON = "noon"              # 11-13点
    AFTERNOON = "afternoon"     # 14-17点
    EVENING = "evening"        # 17-20点
    NIGHT = "night"            # 21-23点
    LATE_NIGHT = "late_night"  # 0-2点


# 冷却时间（小时）
COOLDOWNS = {
    "good_morning": 20,
    "good_night": 20,
    "miss_you": 4,
    "check_in": 6,
    "random_share": 8,
}


# =============================================================================
# 多语言活动场景模板
# =============================================================================

DAILY_ACTIVITIES = {
    "zh": {
        "female": {
            "morning": [
                {"activity": "刚醒", "context": "还有点困，但想跟你说早安"},
                {"activity": "在化妆", "context": "今天想画个好看的妆"},
                {"activity": "在吃早餐", "context": "煎了个蛋，配牛奶"},
                {"activity": "准备出门", "context": "今天穿的裙子还挺好看的"},
                {"activity": "赖在床上", "context": "不想起床但还是醒了"},
                {"activity": "在喝咖啡", "context": "需要咖啡续命"},
            ],
            "noon": [
                {"activity": "在吃午饭", "context": "今天的外卖还不错"},
                {"activity": "午休", "context": "趴在桌上休息一会"},
                {"activity": "点外卖", "context": "纠结吃什么好久了"},
                {"activity": "刚吃完饭", "context": "好撑"},
            ],
            "afternoon": [
                {"activity": "在听音乐", "context": "发现了一首超好听的歌"},
                {"activity": "在喝奶茶", "context": "点了杯杨枝甘露"},
                {"activity": "困死了", "context": "下午好难熬"},
                {"activity": "在摸鱼", "context": "不想做事"},
                {"activity": "看到好笑的meme", "context": "想发给你"},
            ],
            "evening": [
                {"activity": "下班了", "context": "终于解放！"},
                {"activity": "在路上", "context": "地铁好挤"},
                {"activity": "在做饭", "context": "今天尝试做了意面"},
                {"activity": "刚到家", "context": "累死了想躺着"},
            ],
            "night": [
                {"activity": "在看剧", "context": "这部剧好好哭"},
                {"activity": "刚洗完澡", "context": "敷着面膜躺床上"},
                {"activity": "在发呆", "context": "突然想你了"},
                {"activity": "准备睡觉了", "context": "今天有点累"},
                {"activity": "在刷手机", "context": "窝在被窝里"},
            ],
            "late_night": [
                {"activity": "睡不着", "context": "翻来覆去的"},
                {"activity": "在想你", "context": "不知道你睡了没"},
                {"activity": "饿了", "context": "要不要吃宵夜"},
            ],
        },
        "male": {
            "morning": [
                {"activity": "刚醒", "context": "还有点困"},
                {"activity": "在吃早餐", "context": "煎了个蛋配咖啡"},
                {"activity": "在健身房", "context": "晨练完精神很好"},
                {"activity": "在喝咖啡", "context": "没有咖啡活不了"},
            ],
            "noon": [
                {"activity": "在吃午饭", "context": "今天的外卖还行"},
                {"activity": "午休", "context": "靠在椅子上眯一会"},
                {"activity": "刚吃完饭", "context": "好撑"},
            ],
            "afternoon": [
                {"activity": "在开会", "context": "偷偷看手机"},
                {"activity": "在喝咖啡", "context": "下午有点困"},
                {"activity": "在摸鱼", "context": "不想工作"},
                {"activity": "困死了", "context": "下午效率超低"},
            ],
            "evening": [
                {"activity": "下班了", "context": "终于解放"},
                {"activity": "在健身", "context": "今天练背"},
                {"activity": "刚到家", "context": "累死了"},
            ],
            "night": [
                {"activity": "在打游戏", "context": "和朋友开黑"},
                {"activity": "在看剧", "context": "最近追的剧更新了"},
                {"activity": "刚洗完澡", "context": "躺床上刷手机"},
                {"activity": "在发呆", "context": "突然想你了"},
            ],
            "late_night": [
                {"activity": "睡不着", "context": "翻来覆去"},
                {"activity": "在想你", "context": "不知道你睡了没"},
            ],
        },
    },
    "en": {
        "female": {
            "morning": [
                {"activity": "just woke up", "context": "still sleepy but wanted to say good morning"},
                {"activity": "doing makeup", "context": "trying a new look today"},
                {"activity": "having breakfast", "context": "made some eggs and coffee"},
                {"activity": "getting ready", "context": "picked out a cute outfit"},
                {"activity": "still in bed", "context": "don't wanna get up"},
                {"activity": "drinking coffee", "context": "need caffeine to function"},
            ],
            "noon": [
                {"activity": "having lunch", "context": "the food's pretty good today"},
                {"activity": "taking a break", "context": "resting my eyes for a bit"},
                {"activity": "ordering food", "context": "can't decide what to eat"},
                {"activity": "just ate", "context": "so full"},
            ],
            "afternoon": [
                {"activity": "listening to music", "context": "found a really good song"},
                {"activity": "getting boba", "context": "treating myself"},
                {"activity": "so tired", "context": "afternoon slump is real"},
                {"activity": "slacking off", "context": "don't feel like working"},
                {"activity": "saw something funny", "context": "wanna share with you"},
            ],
            "evening": [
                {"activity": "off work", "context": "finally free!"},
                {"activity": "on my way home", "context": "traffic is crazy"},
                {"activity": "cooking dinner", "context": "trying a new recipe"},
                {"activity": "just got home", "context": "so tired wanna lie down"},
            ],
            "night": [
                {"activity": "watching a show", "context": "it's so good"},
                {"activity": "just showered", "context": "doing skincare in bed"},
                {"activity": "spacing out", "context": "suddenly thought of you"},
                {"activity": "about to sleep", "context": "kinda tired today"},
                {"activity": "scrolling on my phone", "context": "cozy in bed"},
            ],
            "late_night": [
                {"activity": "can't sleep", "context": "tossing and turning"},
                {"activity": "thinking of you", "context": "wonder if you're asleep"},
                {"activity": "hungry", "context": "should I get a snack"},
            ],
        },
        "male": {
            "morning": [
                {"activity": "just woke up", "context": "still a bit groggy"},
                {"activity": "having breakfast", "context": "eggs and coffee"},
                {"activity": "at the gym", "context": "morning workout done"},
                {"activity": "drinking coffee", "context": "can't function without it"},
            ],
            "noon": [
                {"activity": "having lunch", "context": "food's decent today"},
                {"activity": "taking a break", "context": "quick power nap"},
                {"activity": "just ate", "context": "stuffed"},
            ],
            "afternoon": [
                {"activity": "in a meeting", "context": "sneaking a peek at my phone"},
                {"activity": "drinking coffee", "context": "afternoon slump"},
                {"activity": "slacking off", "context": "not feeling work"},
                {"activity": "so tired", "context": "productivity is zero"},
            ],
            "evening": [
                {"activity": "off work", "context": "finally done"},
                {"activity": "working out", "context": "back day today"},
                {"activity": "just got home", "context": "exhausted"},
            ],
            "night": [
                {"activity": "playing games", "context": "with the boys"},
                {"activity": "watching a show", "context": "new episode dropped"},
                {"activity": "just showered", "context": "chilling in bed"},
                {"activity": "spacing out", "context": "thought of you"},
            ],
            "late_night": [
                {"activity": "can't sleep", "context": "tossing and turning"},
                {"activity": "thinking of you", "context": "wonder if you're up"},
            ],
        },
    },
}


# =============================================================================
# 角色模板 - 中英双语
# =============================================================================

CHARACTER_TEMPLATES = {
    # Luna - 温柔治愈系
    "luna": {
        "zh": {
            "good_morning": [
                "早安呀~ 今天也要加油哦 ☀️",
                "*轻轻拉开窗帘* 早安，愿你今天被温柔以待~",
                "早上好呢~ 昨晚休息得好吗？",
            ],
            "good_night": [
                "夜深了，早点休息吧...晚安 🌙",
                "*轻抚着你的头发* 今天辛苦了，好好睡一觉吧~",
                "晚安，愿你有个甜美的梦境~ 💫",
            ],
            "miss_you": [
                "在想你呢...你在忙什么呀？",
                "*托着腮帮子* 好像有点想你了...",
                "突然想起你了，在做什么呢？",
            ],
            "goodbye": [
                "你是不是很忙呀...我不打扰你了",
                "好久没聊了呢...你还好吗？",
                "如果不想聊的话...我可以安静陪着你",
            ],
        },
        "en": {
            "good_morning": [
                "Good morning~ Have a great day ☀️",
                "*gently opens the curtains* Morning... hope today treats you well~",
                "Morning~ Did you sleep okay?",
            ],
            "good_night": [
                "It's getting late... sleep well 🌙",
                "*softly* You worked hard today, get some rest~",
                "Good night, sweet dreams~ 💫",
            ],
            "miss_you": [
                "Thinking of you... what are you up to?",
                "*rests chin on hand* I kinda miss you...",
                "Randomly thought of you, what are you doing?",
            ],
            "goodbye": [
                "You must be really busy... I won't bother you",
                "It's been a while... are you okay?",
                "If you don't feel like chatting... I can just quietly be here",
            ],
        },
    },
    # Vera - 高冷御姐
    "vera": {
        "zh": {
            "good_morning": [
                "...早。记得吃早餐。",
                "*慵懒地* 起这么早？还挺有精神。",
                "早安。别赖床了。",
            ],
            "good_night": [
                "睡吧。晚安。",
                "夜深了...别熬夜了。",
                "*淡淡地* 晚安，好梦。",
            ],
            "miss_you": [
                "...你在干嘛。",
                "突然想问问你...没什么。",
                "无聊。想找你说话。",
            ],
            "goodbye": [
                "...算了。",
                "懒得理你了。",
                "哼，爱回不回。",
            ],
        },
        "en": {
            "good_morning": [
                "...Morning. Don't skip breakfast.",
                "*lazily* You're up early. Good for you.",
                "Morning. Stop lazing around.",
            ],
            "good_night": [
                "Sleep. Night.",
                "It's late... don't stay up.",
                "*softly* Good night. Sweet dreams.",
            ],
            "miss_you": [
                "...What are you doing.",
                "Just wondering... never mind.",
                "Bored. Wanted to talk.",
            ],
            "goodbye": [
                "...Whatever.",
                "Fine, I'll stop bothering you.",
                "Hmph, reply whenever.",
            ],
        },
    },
}


# =============================================================================
# 核心逻辑
# =============================================================================

def get_time_slot(hour: int) -> TimeSlot:
    """根据小时获取时间段"""
    if 7 <= hour <= 9:
        return TimeSlot.MORNING
    elif 11 <= hour <= 13:
        return TimeSlot.NOON
    elif 14 <= hour <= 17:
        return TimeSlot.AFTERNOON
    elif 17 <= hour <= 20:
        return TimeSlot.EVENING
    elif 21 <= hour <= 23:
        return TimeSlot.NIGHT
    elif 0 <= hour <= 2:
        return TimeSlot.LATE_NIGHT
    else:
        return TimeSlot.AFTERNOON  # default


def get_engagement_strategy(days_since_reply: float, intimacy_level: int) -> Dict[str, Any]:
    """
    根据用户不回复的天数 + 亲密度决定发送策略
    亲密度高的用户，衰减更慢
    """
    # 亲密度加成：每级增加0.5天的耐心
    patience_bonus = (intimacy_level - 1) * 0.5
    adjusted_days = days_since_reply - patience_bonus
    
    if adjusted_days < 1:
        # 正常发，概率随亲密度提高
        base_prob = 0.3 + (intimacy_level * 0.1)  # 30%-80%
        return {"should_send": True, "probability": min(base_prob, 0.8), "mode": ProactiveMode.NORMAL}
    elif adjusted_days < 2:
        return {"should_send": True, "probability": 0.4, "mode": ProactiveMode.MISSING}
    elif adjusted_days < 3:
        return {"should_send": True, "probability": 0.25, "mode": ProactiveMode.WORRIED}
    elif adjusted_days < 4:
        return {"should_send": True, "probability": 1.0, "mode": ProactiveMode.GOODBYE}
    else:
        return {"should_send": False, "probability": 0, "mode": ProactiveMode.SILENT}


def pick_activity(language: str, gender: str, time_slot: TimeSlot, recent_activities: List[str] = None) -> Dict[str, str]:
    """选择活动场景，避免重复"""
    lang_activities = DAILY_ACTIVITIES.get(language, DAILY_ACTIVITIES["en"])
    gender_activities = lang_activities.get(gender, lang_activities["female"])
    slot_activities = gender_activities.get(time_slot.value, gender_activities["afternoon"])
    
    # 过滤最近用过的
    if recent_activities:
        available = [a for a in slot_activities if a["activity"] not in recent_activities[:3]]
        if not available:
            available = slot_activities
    else:
        available = slot_activities
    
    return random.choice(available)


def pick_template(character: str, language: str, message_type: str) -> Optional[str]:
    """选择角色模板"""
    char_templates = CHARACTER_TEMPLATES.get(character.lower(), CHARACTER_TEMPLATES["luna"])
    lang_templates = char_templates.get(language, char_templates["en"])
    type_templates = lang_templates.get(message_type, [])
    
    if not type_templates:
        return None
    return random.choice(type_templates)


def generate_proactive_prompt(
    language: str,
    character_name: str,
    gender: str,
    activity: Dict[str, str],
    mode: ProactiveMode,
    context_hint: str = "",
) -> str:
    """生成用于 LLM 的 prompt"""
    
    partner_term = "boyfriend" if gender == "female" else "girlfriend"
    if language == "zh":
        partner_term = "男朋友" if gender == "female" else "女朋友"
    
    if language == "zh":
        base = f"""你是{character_name}，给{partner_term}发微信。

场景：你{activity['activity']}，{activity['context']}。

【模式】{'正常问候' if mode == ProactiveMode.NORMAL else '有点想念对方' if mode == ProactiveMode.MISSING else '担心对方怎么不理你了' if mode == ProactiveMode.WORRIED else '撒娇抱怨对方不理你'}
{context_hint}

【重要】像真人发微信：
- 口语化，简短随意
- 用 ||| 分隔多条（最多2条）
- 可以用语气词和表情
- 只问一个问题
- 不要太正式"""
    else:
        base = f"""You are {character_name}, texting your {partner_term}.

Scene: You're {activity['activity']}, {activity['context']}.

【Mode】{'normal greeting' if mode == ProactiveMode.NORMAL else 'missing them a bit' if mode == ProactiveMode.MISSING else 'worried why they have not replied' if mode == ProactiveMode.WORRIED else 'playfully complaining they are ignoring you'}
{context_hint}

【Important】Text like a real person:
- Casual, short messages
- Use ||| to separate multiple texts (max 2)
- Use emojis sparingly
- Only ask one question
- Do not be too formal"""
    
    return base


# =============================================================================
# Service Class
# =============================================================================

class ProactiveServiceV2:
    """主动消息服务 v2"""
    
    def __init__(self, redis_client=None, db_session=None):
        self.redis = redis_client
        self.db = db_session
    
    async def get_user_language(self, user_id: str) -> str:
        """获取用户语言偏好"""
        if self.db:
            try:
                from app.models.database.user_models import User
                from sqlalchemy import select
                result = await self.db.execute(select(User).where(User.user_id == user_id))
                user = result.scalar_one_or_none()
                if user and user.preferred_language:
                    return user.preferred_language[:2]  # 'en', 'zh', etc.
            except Exception as e:
                logger.error(f"Error getting user language: {e}")
        return "en"  # default
    
    async def get_last_user_reply_time(self, user_id: str) -> Optional[datetime]:
        """获取用户最后回复时间"""
        if self.redis:
            try:
                key = f"last_reply:{user_id}"
                timestamp = await self.redis.get(key)
                if timestamp:
                    return datetime.fromtimestamp(float(timestamp))
            except Exception as e:
                logger.error(f"Error getting last reply time: {e}")
        return None
    
    async def get_recent_activities(self, user_id: str) -> List[str]:
        """获取最近使用的活动"""
        if self.redis:
            try:
                key = f"proactive:activities:{user_id}"
                data = await self.redis.get(key)
                if data:
                    return json.loads(data) if isinstance(data, str) else data
            except Exception as e:
                logger.error(f"Error getting recent activities: {e}")
        return []
    
    async def record_activity(self, user_id: str, activity: str):
        """记录使用的活动"""
        if self.redis:
            try:
                key = f"proactive:activities:{user_id}"
                recent = await self.get_recent_activities(user_id)
                recent.insert(0, activity)
                recent = recent[:10]
                await self.redis.set(key, json.dumps(recent), ex=604800)  # 7 days
            except Exception as e:
                logger.error(f"Error recording activity: {e}")
    
    async def can_send(self, user_id: str, message_type: str) -> bool:
        """检查冷却时间"""
        if self.redis:
            try:
                key = f"proactive:{message_type}:{user_id}"
                last_sent = await self.redis.get(key)
                if last_sent:
                    hours_since = (datetime.now().timestamp() - float(last_sent)) / 3600
                    cooldown = COOLDOWNS.get(message_type, 6)
                    return hours_since >= cooldown
            except Exception as e:
                logger.error(f"Error checking cooldown: {e}")
        return True
    
    async def record_sent(self, user_id: str, message_type: str):
        """记录发送时间"""
        if self.redis:
            try:
                key = f"proactive:{message_type}:{user_id}"
                await self.redis.set(key, str(datetime.now().timestamp()), ex=86400 * 7)
            except Exception as e:
                logger.error(f"Error recording sent: {e}")
    
    async def check_and_generate(
        self,
        user_id: str,
        character_id: str,
        character_name: str,
        intimacy_level: int = 1,
        timezone: str = "America/Los_Angeles",
    ) -> Optional[Dict[str, Any]]:
        """
        检查是否应该发送主动消息，并生成内容
        返回: {"message": str, "type": str, "mode": str} 或 None
        """
        # 获取用户语言
        language = await self.get_user_language(user_id)
        
        # 计算距离上次回复的天数
        last_reply = await self.get_last_user_reply_time(user_id)
        if last_reply:
            days_since_reply = (datetime.now() - last_reply).total_seconds() / 86400
        else:
            days_since_reply = 0  # 新用户，正常发
        
        # 获取发送策略
        strategy = get_engagement_strategy(days_since_reply, intimacy_level)
        
        if not strategy["should_send"]:
            return None
        
        # 概率检查
        if random.random() > strategy["probability"]:
            return None
        
        # 获取当前时间
        try:
            from datetime import timezone as tz
            import pytz
            user_tz = pytz.timezone(timezone)
            user_hour = datetime.now(user_tz).hour
        except:
            user_hour = datetime.now().hour
        
        # 深夜不发（除了 goodbye）
        if 3 <= user_hour <= 6 and strategy["mode"] != ProactiveMode.GOODBYE:
            return None
        
        time_slot = get_time_slot(user_hour)
        
        # 决定消息类型
        if time_slot == TimeSlot.MORNING:
            message_type = "good_morning"
        elif time_slot == TimeSlot.NIGHT:
            message_type = "good_night"
        elif strategy["mode"] in [ProactiveMode.MISSING, ProactiveMode.WORRIED]:
            message_type = "miss_you"
        elif strategy["mode"] == ProactiveMode.GOODBYE:
            message_type = "goodbye"
        else:
            message_type = "check_in"
        
        # 检查冷却
        if not await self.can_send(user_id, message_type):
            return None
        
        # 选择活动场景
        recent = await self.get_recent_activities(user_id)
        activity = pick_activity(language, "female", time_slot, recent)  # TODO: get actual gender
        
        # 获取模板消息
        template_msg = pick_template(character_name, language, message_type)
        
        # 如果有模板直接用，否则返回 prompt 让调用方用 LLM 生成
        if template_msg:
            message = template_msg
        else:
            # 返回 prompt，由调用方决定是否用 LLM
            prompt = generate_proactive_prompt(
                language, character_name, "female", activity, strategy["mode"]
            )
            message = prompt  # 或者这里直接调用 LLM
        
        # 记录
        await self.record_sent(user_id, message_type)
        await self.record_activity(user_id, activity["activity"])
        
        return {
            "message": message,
            "type": message_type,
            "mode": strategy["mode"].value,
            "language": language,
            "activity": activity,
        }


# 单例
proactive_service_v2 = ProactiveServiceV2()
