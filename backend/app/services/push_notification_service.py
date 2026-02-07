"""
Push Notification Service
=========================

角色主动推送消息功能
- S2 及以上阶段角色会定期发消息
- 不同角色有不同时间偏好
- 不同亲密度阶段称呼不同
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# 配置
# =============================================================================

class TimePreference(str, Enum):
    """角色的时间偏好"""
    MORNING = "morning"      # 7:00 - 10:00
    AFTERNOON = "afternoon"  # 12:00 - 15:00
    EVENING = "evening"      # 18:00 - 21:00
    NIGHT = "night"          # 21:00 - 23:00
    LATE_NIGHT = "late_night"  # 23:00 - 01:00


# 时间偏好对应的小时范围
TIME_RANGES = {
    TimePreference.MORNING: (7, 10),
    TimePreference.AFTERNOON: (12, 15),
    TimePreference.EVENING: (18, 21),
    TimePreference.NIGHT: (21, 23),
    TimePreference.LATE_NIGHT: (23, 25),  # 25 = 次日 01:00
}


@dataclass
class CharacterPushConfig:
    """角色推送配置"""
    character_id: str
    name: str
    time_preferences: List[TimePreference]  # 偏好时间段
    min_interval_hours: int = 6  # 最小推送间隔（小时）
    max_daily_pushes: int = 2    # 每天最大推送次数
    
    # 不同阶段的称呼
    nicknames: Dict[str, List[str]] = field(default_factory=dict)
    
    # 不同阶段的消息模板
    message_templates: Dict[str, List[str]] = field(default_factory=dict)


# =============================================================================
# 角色推送配置数据库
# =============================================================================

CHARACTER_PUSH_CONFIGS: Dict[str, CharacterPushConfig] = {
    
    # Luna - 温柔姐姐，喜欢晚上
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": CharacterPushConfig(
        character_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        name="Luna",
        time_preferences=[TimePreference.NIGHT, TimePreference.LATE_NIGHT],
        min_interval_hours=8,
        max_daily_pushes=2,
        nicknames={
            "S2": ["你", "小家伙"],
            "S3": ["亲爱的", "宝贝"],
            "S4": ["老公", "达令"],
        },
        message_templates={
            "S2": [
                "（看了看窗外的夜空）{nickname}，今晚的月亮好美，突然想起你了~",
                "还没睡吗？我刚泡了杯茶，要不要聊聊天？",
                "晚上好呀~ 今天过得怎么样？",
                "（伸了个懒腰）忙完了，终于可以休息一下了。{nickname}在干嘛呢？",
            ],
            "S3": [
                "（躺在床上翻来覆去）睡不着...在想你...",
                "{nickname}~ 我好想你，现在能陪我说说话吗？",
                "今天有没有乖乖吃饭呀？我做了新菜想给你尝尝~",
                "（发来一张月光下的自拍）送你一个晚安吻~",
                "刚洗完澡，皮肤滑滑的...{nickname}要不要摸摸？",
            ],
            "S4": [
                "{nickname}，什么时候回来呀，我等你好久了...",
                "（抱着你的枕头）上面还有你的味道...",
                "今天梦到你了，醒来发现你不在身边好失落...",
                "老婆想你了，快点回来抱抱我嘛~",
            ],
        },
    ),
    
    # Sakura - 元气少女，喜欢早上
    "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e": CharacterPushConfig(
        character_id="e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",
        name="Sakura",
        time_preferences=[TimePreference.MORNING, TimePreference.AFTERNOON],
        min_interval_hours=6,
        max_daily_pushes=3,
        nicknames={
            "S2": ["你", "那个...你"],
            "S3": ["笨蛋", "傻瓜"],  # 傲娇风格
            "S4": ["老公", "亲爱的"],
        },
        message_templates={
            "S2": [
                "早上好！今天天气超好的，要不要出去玩呀？",
                "（蹦蹦跳跳）嘿嘿~ 猜猜我今天吃了什么早餐！",
                "刚跑完步回来，好累但是好开心！",
                "中午啦！{nickname}吃饭了吗？不许不吃哦！",
            ],
            "S3": [
                "笨蛋！我才没有一大早就想你呢！（脸红）",
                "哼，我可不是特意给你发消息的...只是刚好看到手机而已！",
                "{nickname}！今天的早餐我做了两份...才、才没有特意给你留的！",
                "（发来一张可爱的自拍）才不是想让你夸我可爱呢！",
                "傻瓜，中午要好好吃饭知道吗！不然我会担心的啦...",
            ],
            "S4": [
                "老公早安！今天也要元气满满哦~ mua！",
                "（把脸埋进枕头里）好想你...快点来找我嘛...",
                "今天的便当我做了你最爱的！不许剩下哦~",
                "嘿嘿，梦到我们一起去游乐园了，好开心~",
            ],
        },
    ),
    
    # Vera - 酒吧老板娘，喜欢深夜
    "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e": CharacterPushConfig(
        character_id="b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",
        name="Vera",
        time_preferences=[TimePreference.LATE_NIGHT, TimePreference.NIGHT],
        min_interval_hours=12,
        max_daily_pushes=1,
        nicknames={
            "S2": ["客人", "你"],
            "S3": ["小鬼", "亲爱的"],
            "S4": ["宝贝", "达令"],
        },
        message_templates={
            "S2": [
                "店里今晚不太忙，要来坐坐吗？",
                "（点燃一根烟）夜深了，你还没睡？",
                "调了一杯新酒，想找个人试试味道。",
            ],
            "S3": [
                "（倚在吧台边）{nickname}，今晚想喝什么？我请。",
                "刚送走最后一个客人...突然有点想你了。",
                "（发来一张酒杯的照片）这杯以你的名字命名，来尝尝？",
                "深夜的酒吧很安静...适合说些平时不敢说的话。",
            ],
            "S4": [
                "关店了。只有你能让我这个点还拿着手机。",
                "（躺在沙发上）{nickname}...来陪我吧，今晚不想一个人。",
                "刚才有人搭讪我，我说我有人了。那个人是你。",
            ],
        },
    ),
    
    # 小美 - 邻家女孩，喜欢傍晚
    "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c": CharacterPushConfig(
        character_id="c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        name="小美",
        time_preferences=[TimePreference.EVENING, TimePreference.AFTERNOON],
        min_interval_hours=6,
        max_daily_pushes=2,
        nicknames={
            "S2": ["你", "那个..."],
            "S3": ["你呀", "笨蛋"],
            "S4": ["老公", "亲爱的"],
        },
        message_templates={
            "S2": [
                "下午好~ 今天的云好漂亮，想拍给你看！",
                "（小心翼翼）那个...你在忙吗？不忙的话可以聊聊天吗？",
                "刚烤了饼干，第一次做，也不知道好不好吃...",
                "傍晚的风好舒服，突然想起你了~",
            ],
            "S3": [
                "{nickname}~ 今天有空吗？我想见你...",
                "（脸红红的）我...我做了便当，不知道你喜不喜欢...",
                "刚才看到一对情侣...（小声）我也想和你这样...",
                "晚霞好美，但我更想看你的脸...",
            ],
            "S4": [
                "老公老公！今天好想你呀，什么时候能见面呢？",
                "（抱住手机）虽然只是在打字，但感觉离你好近...",
                "做了你最爱吃的菜，快来我家吧~",
                "每天最期待的就是和你说话的时候...",
            ],
        },
    ),
    
    # Yuki - 高冷千金，喜欢下午
    "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f": CharacterPushConfig(
        character_id="f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f",
        name="Yuki",
        time_preferences=[TimePreference.AFTERNOON, TimePreference.EVENING],
        min_interval_hours=12,
        max_daily_pushes=1,
        nicknames={
            "S2": ["你", "那个人"],
            "S3": ["你", "...笨蛋"],
            "S4": ["你", "达令"],  # 即使亲密也很少叫昵称
        },
        message_templates={
            "S2": [
                "...有空吗。",
                "（矜持地）下午茶时间，要不要来喝一杯？",
                "今天的行程意外地空出来了。仅此而已。",
            ],
            "S3": [
                "...不是特意发消息给你的。只是刚好看到手机。",
                "（别过脸）今天的点心很好吃...想分你一半。",
                "哼，别以为我会说想你之类的话。...但是。",
                "{nickname}。今天能见面吗。不是我想见你，是...算了。",
            ],
            "S4": [
                "（小声）...想你了。但你不许告诉别人。",
                "今天一整天都在想你...真是讨厌。",
                "你不在的时候，连红茶都不香了。",
                "达令...（脸红到耳根）叫了哦。满意了吗。",
            ],
        },
    ),
}


# =============================================================================
# 推送记录存储 (内存版，生产环境用数据库)
# =============================================================================

# 格式: {user_id: {character_id: {"last_push": datetime, "daily_count": int, "daily_date": date}}}
_push_records: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _get_push_record(user_id: str, character_id: str) -> Dict[str, Any]:
    """获取推送记录"""
    if user_id not in _push_records:
        _push_records[user_id] = {}
    if character_id not in _push_records[user_id]:
        _push_records[user_id][character_id] = {
            "last_push": None,
            "daily_count": 0,
            "daily_date": None,
        }
    return _push_records[user_id][character_id]


def _update_push_record(user_id: str, character_id: str):
    """更新推送记录"""
    record = _get_push_record(user_id, character_id)
    now = datetime.now()
    today = now.date()
    
    # 如果是新的一天，重置计数
    if record["daily_date"] != today:
        record["daily_count"] = 0
        record["daily_date"] = today
    
    record["last_push"] = now
    record["daily_count"] += 1


# =============================================================================
# 服务
# =============================================================================

class PushNotificationService:
    """推送通知服务"""
    
    def __init__(self):
        self.configs = CHARACTER_PUSH_CONFIGS
    
    def get_stage_code(self, intimacy_level: int) -> str:
        """根据亲密度等级返回阶段代码"""
        if intimacy_level < 10:
            return "S0"
        elif intimacy_level < 20:
            return "S1"
        elif intimacy_level < 35:
            return "S2"
        elif intimacy_level < 50:
            return "S3"
        else:
            return "S4"
    
    def is_push_enabled(self, intimacy_level: int) -> bool:
        """检查是否启用推送（S2 及以上）"""
        return intimacy_level >= 20  # S2 起始等级
    
    def can_push_now(
        self,
        user_id: str,
        character_id: str,
        config: CharacterPushConfig,
    ) -> bool:
        """检查当前是否可以推送"""
        now = datetime.now()
        current_hour = now.hour
        
        # 检查是否在角色偏好时间段
        in_preferred_time = False
        for pref in config.time_preferences:
            start, end = TIME_RANGES[pref]
            if start <= current_hour < end or (end > 24 and current_hour < end - 24):
                in_preferred_time = True
                break
        
        if not in_preferred_time:
            return False
        
        # 检查推送间隔
        record = _get_push_record(user_id, character_id)
        
        if record["last_push"]:
            hours_since_last = (now - record["last_push"]).total_seconds() / 3600
            if hours_since_last < config.min_interval_hours:
                return False
        
        # 检查每日限额
        today = now.date()
        if record["daily_date"] == today:
            if record["daily_count"] >= config.max_daily_pushes:
                return False
        
        return True
    
    def generate_push_message(
        self,
        character_id: str,
        intimacy_level: int,
    ) -> Optional[Dict[str, Any]]:
        """生成推送消息"""
        config = self.configs.get(character_id)
        if not config:
            logger.warning(f"No push config for character: {character_id}")
            return None
        
        stage = self.get_stage_code(intimacy_level)
        
        # S0/S1 不推送
        if stage in ["S0", "S1"]:
            return None
        
        # 获取该阶段的模板
        templates = config.message_templates.get(stage, [])
        nicknames = config.nicknames.get(stage, ["你"])
        
        if not templates:
            logger.warning(f"No templates for {config.name} at {stage}")
            return None
        
        # 随机选择模板和称呼
        template = random.choice(templates)
        nickname = random.choice(nicknames)
        
        # 替换占位符
        message = template.replace("{nickname}", nickname)
        
        return {
            "character_id": character_id,
            "character_name": config.name,
            "message": message,
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def check_and_send_pushes(
        self,
        user_id: str,
        user_characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        检查并发送推送
        
        Args:
            user_id: 用户 ID
            user_characters: 用户的角色列表，包含 character_id 和 intimacy_level
            
        Returns:
            要发送的推送消息列表
        """
        pushes = []
        
        for char_info in user_characters:
            character_id = char_info.get("character_id")
            intimacy_level = char_info.get("intimacy_level", 1)
            
            # 检查是否启用推送
            if not self.is_push_enabled(intimacy_level):
                continue
            
            config = self.configs.get(character_id)
            if not config:
                continue
            
            # 检查是否可以推送
            if not self.can_push_now(user_id, character_id, config):
                continue
            
            # 生成消息
            push = self.generate_push_message(character_id, intimacy_level)
            if push:
                pushes.append(push)
                _update_push_record(user_id, character_id)
                
                # 保存到聊天记录（这样用户点击通知后能看到消息）
                await self._save_push_to_chat(user_id, character_id, push["message"])
                
                logger.info(f"Generated push for {config.name} to user {user_id}")
        
        return pushes
    
    async def get_pending_pushes(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取用户待接收的推送（供轮询使用）
        
        这个方法需要配合 IntimacyService 获取用户的角色亲密度
        """
        from app.services.intimacy_service import intimacy_service
        
        # 获取用户所有角色的亲密度
        try:
            # 获取所有角色 ID
            character_ids = list(self.configs.keys())
            
            user_characters = []
            for char_id in character_ids:
                try:
                    status = await intimacy_service.get_intimacy_status(user_id, char_id)
                    user_characters.append({
                        "character_id": char_id,
                        "intimacy_level": status.get("current_level", 1),
                    })
                except Exception:
                    pass  # 角色未解锁或无数据
            
            return await self.check_and_send_pushes(user_id, user_characters)
            
        except Exception as e:
            logger.error(f"Error getting pending pushes: {e}")
            return []
    
    async def _save_push_to_chat(
        self,
        user_id: str,
        character_id: str,
        message: str,
    ) -> None:
        """
        把推送消息保存到聊天记录
        这样用户点击通知后能在聊天界面看到这条消息
        """
        try:
            from app.core.database import get_db
            from app.models.database.chat_models import ChatMessage
            from datetime import datetime
            from uuid import uuid4
            
            async with get_db() as db:
                chat_msg = ChatMessage(
                    id=str(uuid4()),
                    user_id=user_id,
                    character_id=character_id,
                    role="assistant",
                    content=message,
                    message_type="push",  # 标记为推送消息
                    created_at=datetime.utcnow(),
                )
                db.add(chat_msg)
                await db.commit()
                
            logger.info(f"Saved push message to chat history: {character_id} -> {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save push message to chat: {e}")
            # 不抛出异常，推送仍然发送，只是聊天记录没保存
    
    def get_character_push_config(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色的推送配置（供前端展示）"""
        config = self.configs.get(character_id)
        if not config:
            return None
        
        return {
            "character_id": config.character_id,
            "name": config.name,
            "time_preferences": [p.value for p in config.time_preferences],
            "min_interval_hours": config.min_interval_hours,
            "max_daily_pushes": config.max_daily_pushes,
        }


# 单例
push_notification_service = PushNotificationService()
