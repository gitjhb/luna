"""
Event Message Model
===================

通用事件消息格式，用于在聊天历史中存储各种事件（约会、礼物、里程碑等）。

设计原则：
1. 结构化JSON存储，便于前端渲染和后端处理
2. summary 字段用于AI上下文，减少token消耗
3. detail_id 关联详情（回忆录等），支持付费解锁
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import json


class EventMessageType(str, Enum):
    """事件类型"""
    DATE = "date"              # 约会
    GIFT = "gift"              # 礼物
    MILESTONE = "milestone"    # 里程碑（升级、成就等）
    MOOD = "mood"              # 情绪变化
    CONFESSION = "confession"  # 表白
    KISS = "kiss"              # 初吻
    INTIMATE = "intimate"      # 亲密时刻


# 事件图标映射
EVENT_ICONS = {
    EventMessageType.DATE: "💕",
    EventMessageType.GIFT: "🎁",
    EventMessageType.MILESTONE: "🎉",
    EventMessageType.MOOD: "💭",
    EventMessageType.CONFESSION: "💝",
    EventMessageType.KISS: "💋",
    EventMessageType.INTIMATE: "🔥",
}

# 事件显示名称
EVENT_NAMES = {
    EventMessageType.DATE: "约会",
    EventMessageType.GIFT: "礼物",
    EventMessageType.MILESTONE: "里程碑",
    EventMessageType.MOOD: "心情变化",
    EventMessageType.CONFESSION: "表白",
    EventMessageType.KISS: "初吻",
    EventMessageType.INTIMATE: "亲密时刻",
}


@dataclass
class EventMessageDisplay:
    """事件显示信息"""
    title: str
    subtitle: str
    

@dataclass
class EventMessage:
    """
    通用事件消息格式
    
    Example:
    {
        "type": "event",
        "event_type": "date",
        "summary": "星空露营 · 愉快的约会",
        "detail_id": "xxx",
        "icon": "💕",
        "display": {
            "title": "星空露营",
            "subtitle": "愉快的约会"
        },
        "unlock_cost": 10,
        "is_unlocked": false
    }
    """
    type: str = "event"  # 固定为 "event"
    event_type: str = ""  # date, gift, milestone, etc.
    summary: str = ""     # 给AI的简短概括
    detail_id: Optional[str] = None  # 关联的详情ID（如回忆录ID）
    icon: str = ""
    display: Optional[EventMessageDisplay] = None
    unlock_cost: int = 0  # 解锁所需月石，0表示免费
    is_unlocked: bool = False  # 是否已解锁
    metadata: Optional[Dict[str, Any]] = None  # 额外数据
    
    def to_json(self) -> str:
        """序列化为JSON字符串（存入数据库）"""
        data = {
            "type": self.type,
            "event_type": self.event_type,
            "summary": self.summary,
            "icon": self.icon,
            "unlock_cost": self.unlock_cost,
            "is_unlocked": self.is_unlocked,
        }
        if self.detail_id:
            data["detail_id"] = self.detail_id
        if self.display:
            data["display"] = {
                "title": self.display.title,
                "subtitle": self.display.subtitle,
            }
        if self.metadata:
            data["metadata"] = self.metadata
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> Optional["EventMessage"]:
        """从JSON字符串解析"""
        try:
            data = json.loads(json_str)
            if data.get("type") != "event":
                return None
            
            display = None
            if "display" in data:
                display = EventMessageDisplay(
                    title=data["display"].get("title", ""),
                    subtitle=data["display"].get("subtitle", ""),
                )
            
            return cls(
                type="event",
                event_type=data.get("event_type", ""),
                summary=data.get("summary", ""),
                detail_id=data.get("detail_id"),
                icon=data.get("icon", ""),
                display=display,
                unlock_cost=data.get("unlock_cost", 0),
                is_unlocked=data.get("is_unlocked", False),
                metadata=data.get("metadata"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
    
    @classmethod
    def is_event_message(cls, content: str) -> bool:
        """检查消息内容是否是事件消息"""
        try:
            data = json.loads(content)
            return data.get("type") == "event"
        except (json.JSONDecodeError, TypeError):
            return False
    
    @classmethod
    def extract_summary(cls, content: str) -> Optional[str]:
        """从事件消息中提取summary（用于AI上下文）"""
        event = cls.from_json(content)
        if event:
            return f"[{EVENT_NAMES.get(event.event_type, '事件')}] {event.summary}"
        return None


def create_date_event(
    scenario_name: str,
    ending_text: str,
    detail_id: Optional[str] = None,
    unlock_cost: int = 10,
    # 新增字段 - 约会卡片完整信息
    ending_type: Optional[str] = None,  # perfect/good/normal/bad
    progress: Optional[str] = None,      # "5/5"
    affection: Optional[int] = None,     # 好感度分数
    rewards: Optional[Dict[str, Any]] = None,  # {"xp": 150, "emotion": 30}
    story_summary: Optional[str] = None,  # 简短的约会回忆描述
) -> EventMessage:
    """
    创建约会事件消息
    
    支持完整的约会卡片信息，前端可渲染为特殊卡片样式
    """
    # 构建 metadata，包含卡片渲染需要的完整信息
    metadata = {
        "date_card": True,  # 标记这是约会卡片，前端特殊处理
    }
    
    if ending_type:
        metadata["ending"] = ending_type
    if progress:
        metadata["progress"] = progress
    if affection is not None:
        metadata["affection"] = affection
    if rewards:
        metadata["rewards"] = rewards
    if story_summary:
        metadata["summary"] = story_summary
    
    return EventMessage(
        event_type=EventMessageType.DATE,
        summary=f"{scenario_name} · {ending_text}",
        detail_id=detail_id,
        icon=EVENT_ICONS[EventMessageType.DATE],
        display=EventMessageDisplay(
            title=scenario_name,
            subtitle=ending_text,
        ),
        unlock_cost=unlock_cost,
        metadata=metadata if metadata else None,
    )


def create_gift_event(
    gift_name: str,
    gift_icon: str,
    detail_id: Optional[str] = None,
) -> EventMessage:
    """创建礼物事件消息"""
    return EventMessage(
        event_type=EventMessageType.GIFT,
        summary=f"收到礼物：{gift_icon} {gift_name}",
        detail_id=detail_id,
        icon=EVENT_ICONS[EventMessageType.GIFT],
        display=EventMessageDisplay(
            title="收到礼物",
            subtitle=f"{gift_icon} {gift_name}",
        ),
        unlock_cost=0,  # 礼物事件免费查看
    )


def create_milestone_event(
    milestone_name: str,
    description: str,
    icon: str = "🎉",
    detail_id: Optional[str] = None,
) -> EventMessage:
    """创建里程碑事件消息"""
    return EventMessage(
        event_type=EventMessageType.MILESTONE,
        summary=f"{milestone_name}: {description}",
        detail_id=detail_id,
        icon=icon,
        display=EventMessageDisplay(
            title=milestone_name,
            subtitle=description,
        ),
        unlock_cost=0,  # 里程碑免费
    )


def create_confession_event(
    detail_id: Optional[str] = None,
    unlock_cost: int = 15,
) -> EventMessage:
    """创建表白事件消息"""
    return EventMessage(
        event_type=EventMessageType.CONFESSION,
        summary="难忘的表白时刻",
        detail_id=detail_id,
        icon=EVENT_ICONS[EventMessageType.CONFESSION],
        display=EventMessageDisplay(
            title="表白",
            subtitle="心跳加速的瞬间",
        ),
        unlock_cost=unlock_cost,
    )


def create_kiss_event(
    detail_id: Optional[str] = None,
    unlock_cost: int = 20,
) -> EventMessage:
    """创建初吻事件消息"""
    return EventMessage(
        event_type=EventMessageType.KISS,
        summary="甜蜜的初吻",
        detail_id=detail_id,
        icon=EVENT_ICONS[EventMessageType.KISS],
        display=EventMessageDisplay(
            title="初吻",
            subtitle="难忘的瞬间",
        ),
        unlock_cost=unlock_cost,
    )
