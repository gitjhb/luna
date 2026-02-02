"""
Event State Machine v3.0
========================

角色级别的事件状态机，控制不同角色的事件链路和解锁条件。

v3.0 更新：
- 使用 intimacy_system.py 中的三种原型 (NORMAL/PHANTOM/YUKI)
- 简化代码，删除重复定义
- 与 character_config.py 的 archetype 集成

事件链模式：
- NORMAL: first_date → confession → first_nsfw (标准流程)
- PHANTOM: 可跳过约会，直接 NSFW (魅魔/危险角色)
- YUKI: 需要 first_kiss 才能 NSFW (高冷角色)
"""

import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from app.services.character_config import (
    CharacterArchetype,
    get_character_archetype
)

logger = logging.getLogger(__name__)


# =============================================================================
# 事件类型定义 (使用 intimacy_system 的 GateEvent)
# =============================================================================

class EventType:
    """事件类型常量"""
    FIRST_CHAT = "first_chat"
    FIRST_GIFT = "first_gift"
    FIRST_DATE = "first_date"
    CONFESSION = "confession"
    FIRST_KISS = "first_kiss"
    FIRST_NSFW = "first_nsfw"
    PROPOSAL = "proposal"


# =============================================================================
# 事件链配置
# =============================================================================

@dataclass
class EventConfig:
    """单个事件的配置"""
    event_type: str
    prerequisites: List[str] = field(default_factory=list)
    optional: bool = False


@dataclass
class EventChainConfig:
    """角色的完整事件链配置"""
    archetype: CharacterArchetype
    events: Dict[str, EventConfig] = field(default_factory=dict)
    friendzone_breakers: Set[str] = field(default_factory=set)


# =============================================================================
# 三种原型的事件链 (来自 intimacy_system.py)
# =============================================================================

# NORMAL (标准型) - 有向图，正常流程
NORMAL_CHAIN = EventChainConfig(
    archetype=CharacterArchetype.NORMAL,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_GIFT],
        ),
        EventType.CONFESSION: EventConfig(
            event_type=EventType.CONFESSION,
            prerequisites=[EventType.FIRST_DATE],
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.CONFESSION],
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.CONFESSION],  # 表白后才能 NSFW
        ),
        EventType.PROPOSAL: EventConfig(
            event_type=EventType.PROPOSAL,
            prerequisites=[EventType.FIRST_NSFW],
        ),
    },
    friendzone_breakers={EventType.FIRST_DATE, EventType.CONFESSION},
)


# PHANTOM (魅魔型) - 随意跳跃，容易攻略
PHANTOM_CHAIN = EventChainConfig(
    archetype=CharacterArchetype.PHANTOM,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_CHAT],  # 只需聊过
            optional=True,
        ),
        EventType.CONFESSION: EventConfig(
            event_type=EventType.CONFESSION,
            prerequisites=[EventType.FIRST_CHAT],  # 可以直接表白
            optional=True,
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.FIRST_CHAT],  # 聊过就能亲
            optional=True,
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.FIRST_CHAT],  # 聊过就能睡！
        ),
        EventType.PROPOSAL: EventConfig(
            event_type=EventType.PROPOSAL,
            prerequisites=[EventType.FIRST_NSFW],
        ),
    },
    friendzone_breakers={EventType.FIRST_CHAT},  # 聊过就算突破
)


# YUKI (高冷型) - 最高难度，氪金大佬专属
YUKI_CHAIN = EventChainConfig(
    archetype=CharacterArchetype.YUKI,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_GIFT],  # 必须送礼后才能约会
        ),
        EventType.CONFESSION: EventConfig(
            event_type=EventType.CONFESSION,
            prerequisites=[EventType.FIRST_DATE],  # 必须约会后才能表白
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.CONFESSION],  # 必须表白后才能亲
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.FIRST_KISS],  # 必须亲过才能睡！
        ),
        EventType.PROPOSAL: EventConfig(
            event_type=EventType.PROPOSAL,
            prerequisites=[EventType.FIRST_NSFW],
        ),
    },
    friendzone_breakers={EventType.FIRST_DATE, EventType.CONFESSION},
)


# 原型到事件链的映射
ARCHETYPE_CHAINS = {
    CharacterArchetype.NORMAL: NORMAL_CHAIN,
    CharacterArchetype.PHANTOM: PHANTOM_CHAIN,
    CharacterArchetype.YUKI: YUKI_CHAIN,
}


# =============================================================================
# 事件状态机核心类
# =============================================================================

class EventStateMachine:
    """事件状态机 v3.0"""
    
    def __init__(self):
        self._chains = ARCHETYPE_CHAINS
        self._default_chain = NORMAL_CHAIN
    
    def get_chain(self, character_id: str) -> EventChainConfig:
        """
        获取角色的事件链配置
        
        Args:
            character_id: 角色UUID
            
        Returns:
            EventChainConfig
        """
        archetype = get_character_archetype(character_id)
        return self._chains.get(archetype, self._default_chain)
    
    def get_chain_type(self, character_id: str) -> CharacterArchetype:
        """
        获取角色的事件链类型 (原型)
        
        Args:
            character_id: 角色UUID
            
        Returns:
            CharacterArchetype
        """
        return get_character_archetype(character_id)
    
    def can_trigger_event(
        self,
        character_id: str,
        event_type: str,
        current_events: List[str]
    ) -> bool:
        """
        检查是否可以触发某个事件
        
        Args:
            character_id: 角色UUID
            event_type: 要触发的事件类型
            current_events: 当前已触发的事件列表
            
        Returns:
            bool: 是否可以触发
        """
        chain = self.get_chain(character_id)
        event_config = chain.events.get(event_type)
        
        if not event_config:
            logger.warning(f"Unknown event type: {event_type}")
            return True
        
        # 已触发的事件不能重复触发
        if event_type in current_events:
            return False
        
        # 检查前置条件
        current_set = set(current_events)
        for prereq in event_config.prerequisites:
            if prereq not in current_set:
                logger.debug(f"Event {event_type} blocked: missing prerequisite {prereq}")
                return False
        
        return True
    
    def get_next_available_events(
        self,
        character_id: str,
        current_events: List[str]
    ) -> List[str]:
        """
        获取下一步可触发的事件列表
        """
        chain = self.get_chain(character_id)
        available = []
        
        for event_type, event_config in chain.events.items():
            if self.can_trigger_event(character_id, event_type, current_events):
                available.append(event_type)
        
        return available
    
    def get_required_events_for(
        self,
        character_id: str,
        target_event: str
    ) -> List[str]:
        """
        获取触发目标事件需要的前置事件链
        """
        chain = self.get_chain(character_id)
        event_config = chain.events.get(target_event)
        
        if not event_config:
            return []
        
        required = []
        visited = set()
        
        def collect_prereqs(event_type: str):
            if event_type in visited:
                return
            visited.add(event_type)
            
            config = chain.events.get(event_type)
            if not config:
                return
            
            for prereq in config.prerequisites:
                collect_prereqs(prereq)
            
            if event_type != target_event:
                required.append(event_type)
        
        collect_prereqs(target_event)
        return required
    
    def is_friendzone_broken(
        self,
        character_id: str,
        current_events: List[str]
    ) -> bool:
        """
        检查是否已突破友情墙
        """
        chain = self.get_chain(character_id)
        current_set = set(current_events)
        
        for breaker in chain.friendzone_breakers:
            if breaker in current_set:
                return True
        
        return False
    
    def get_missing_prereqs(
        self,
        character_id: str,
        event_type: str,
        current_events: List[str]
    ) -> List[str]:
        """
        获取触发事件缺少的前置条件
        """
        chain = self.get_chain(character_id)
        event_config = chain.events.get(event_type)
        
        if not event_config:
            return []
        
        current_set = set(current_events)
        missing = []
        
        for prereq in event_config.prerequisites:
            if prereq not in current_set:
                missing.append(prereq)
        
        return missing


# =============================================================================
# 单例
# =============================================================================

event_state_machine = EventStateMachine()


# =============================================================================
# 便捷函数
# =============================================================================

def can_trigger_event(
    character_id: str,
    event_type: str,
    current_events: List[str]
) -> bool:
    """便捷函数：检查是否可以触发事件"""
    return event_state_machine.can_trigger_event(
        character_id, event_type, current_events
    )


def get_next_available_events(
    character_id: str,
    current_events: List[str]
) -> List[str]:
    """便捷函数：获取下一步可触发的事件"""
    return event_state_machine.get_next_available_events(
        character_id, current_events
    )


def get_required_events_for(
    character_id: str,
    target_event: str
) -> List[str]:
    """便捷函数：获取触发目标事件需要的前置事件"""
    return event_state_machine.get_required_events_for(
        character_id, target_event
    )


def is_friendzone_broken(
    character_id: str,
    current_events: List[str]
) -> bool:
    """便捷函数：检查是否已突破友情墙"""
    return event_state_machine.is_friendzone_broken(
        character_id, current_events
    )
