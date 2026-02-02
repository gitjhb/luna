"""
Event State Machine
===================

角色级别的事件状态机，控制不同角色的事件链路和解锁条件。

核心设计：
- 每个角色有不同的事件链配置
- 事件有前置条件（prerequisite events）
- 支持查询下一个可用事件、检查是否可触发、获取所需前置

事件链模式：
- normal: first_date → first_confession → first_nsfw (标准流程)
- phantom: 可跳过约会，直接 NSFW (魅魔/危险角色)
- yuki: 需要 first_kiss 才能 NSFW (高冷角色)
"""

import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# 事件类型定义
# =============================================================================

class EventType(str, Enum):
    """所有可能的事件类型"""
    FIRST_CHAT = "first_chat"
    FIRST_COMPLIMENT = "first_compliment"
    FIRST_GIFT = "first_gift"
    FIRST_DATE = "first_date"
    FIRST_KISS = "first_kiss"
    FIRST_CONFESSION = "first_confession"
    FIRST_NSFW = "first_nsfw"
    FIRST_HEARTBREAK = "first_heartbreak"  # 表白失败
    COLD_WAR_SURVIVED = "cold_war_survived"  # 从冷战恢复


class EventChainType(str, Enum):
    """事件链类型"""
    NORMAL = "normal"      # 标准流程
    PHANTOM = "phantom"    # 魅魔模式（可跳过）
    YUKI = "yuki"          # 高冷模式（额外要求）


# =============================================================================
# 事件链配置
# =============================================================================

@dataclass
class EventConfig:
    """单个事件的配置"""
    event_type: str
    prerequisites: List[str] = field(default_factory=list)  # 前置事件
    optional: bool = False  # 是否可选（可跳过）


@dataclass
class EventChainConfig:
    """角色的完整事件链配置"""
    chain_type: EventChainType
    events: Dict[str, EventConfig] = field(default_factory=dict)
    
    # 友情墙突破条件（满足其一即可）
    friendzone_breakers: Set[str] = field(default_factory=set)


# =============================================================================
# 预定义事件链
# =============================================================================

# 标准事件链：first_date → first_confession → first_nsfw
NORMAL_CHAIN = EventChainConfig(
    chain_type=EventChainType.NORMAL,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_COMPLIMENT: EventConfig(
            event_type=EventType.FIRST_COMPLIMENT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.FIRST_DATE],
            optional=True,  # 可选
        ),
        EventType.FIRST_CONFESSION: EventConfig(
            event_type=EventType.FIRST_CONFESSION,
            prerequisites=[EventType.FIRST_DATE],  # 必须先约会
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.FIRST_CONFESSION],  # 必须先表白
        ),
    },
    friendzone_breakers={EventType.FIRST_DATE, EventType.FIRST_CONFESSION},
)


# 魅魔/危险角色事件链：可跳过约会/表白，直接 NSFW
PHANTOM_CHAIN = EventChainConfig(
    chain_type=EventChainType.PHANTOM,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_COMPLIMENT: EventConfig(
            event_type=EventType.FIRST_COMPLIMENT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_CHAT],
            optional=True,  # 可选
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.FIRST_CHAT],  # 只需聊天
            optional=True,
        ),
        EventType.FIRST_CONFESSION: EventConfig(
            event_type=EventType.FIRST_CONFESSION,
            prerequisites=[EventType.FIRST_CHAT],  # 可以直接表白
            optional=True,  # 可选
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.FIRST_CHAT],  # 只需聊过就可以！
        ),
    },
    friendzone_breakers={EventType.FIRST_CHAT},  # 聊过就算突破
)


# 高冷角色事件链：需要 first_kiss 才能 NSFW
YUKI_CHAIN = EventChainConfig(
    chain_type=EventChainType.YUKI,
    events={
        EventType.FIRST_CHAT: EventConfig(
            event_type=EventType.FIRST_CHAT,
            prerequisites=[],
        ),
        EventType.FIRST_COMPLIMENT: EventConfig(
            event_type=EventType.FIRST_COMPLIMENT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_GIFT: EventConfig(
            event_type=EventType.FIRST_GIFT,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_DATE: EventConfig(
            event_type=EventType.FIRST_DATE,
            prerequisites=[EventType.FIRST_CHAT],
        ),
        EventType.FIRST_CONFESSION: EventConfig(
            event_type=EventType.FIRST_CONFESSION,
            prerequisites=[EventType.FIRST_DATE],
        ),
        EventType.FIRST_KISS: EventConfig(
            event_type=EventType.FIRST_KISS,
            prerequisites=[EventType.FIRST_CONFESSION],  # 必须先表白
        ),
        EventType.FIRST_NSFW: EventConfig(
            event_type=EventType.FIRST_NSFW,
            prerequisites=[EventType.FIRST_KISS],  # 必须先接吻！
        ),
    },
    friendzone_breakers={EventType.FIRST_DATE, EventType.FIRST_CONFESSION},
)


# =============================================================================
# 角色到事件链的映射
# =============================================================================

# 角色ID常量
CHARACTER_IDS = {
    "xiaomei": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "luna": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
    "sakura": "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",
    "yuki": "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f",
    "mei": "a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d",
    "phantom": "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",
}

# 角色到事件链的映射
CHARACTER_EVENT_CHAINS: Dict[str, EventChainConfig] = {
    # 魅影 - 魅魔模式
    CHARACTER_IDS["phantom"]: PHANTOM_CHAIN,
    
    # Yuki - 高冷模式
    CHARACTER_IDS["yuki"]: YUKI_CHAIN,
    
    # 其他角色 - 标准模式
    CHARACTER_IDS["xiaomei"]: NORMAL_CHAIN,
    CHARACTER_IDS["luna"]: NORMAL_CHAIN,
    CHARACTER_IDS["sakura"]: NORMAL_CHAIN,
    CHARACTER_IDS["mei"]: NORMAL_CHAIN,
}


# =============================================================================
# 事件状态机核心类
# =============================================================================

class EventStateMachine:
    """事件状态机"""
    
    def __init__(self):
        self._chains = CHARACTER_EVENT_CHAINS
        self._default_chain = NORMAL_CHAIN
    
    def get_chain(self, character_id: str) -> EventChainConfig:
        """
        获取角色的事件链配置
        
        Args:
            character_id: 角色UUID
            
        Returns:
            EventChainConfig
        """
        return self._chains.get(str(character_id), self._default_chain)
    
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
            # 未知事件类型，允许（向后兼容）
            logger.warning(f"Unknown event type: {event_type}")
            return True
        
        # 已触发的事件不能重复触发
        if event_type in current_events:
            return False
        
        # 检查前置条件
        current_set = set(current_events)
        for prereq in event_config.prerequisites:
            if prereq not in current_set:
                logger.debug(
                    f"Event {event_type} blocked: missing prerequisite {prereq}"
                )
                return False
        
        return True
    
    def get_next_available_events(
        self,
        character_id: str,
        current_events: List[str]
    ) -> List[str]:
        """
        获取下一步可触发的事件列表
        
        Args:
            character_id: 角色UUID
            current_events: 当前已触发的事件列表
            
        Returns:
            List[str]: 可触发的事件类型列表
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
        
        Args:
            character_id: 角色UUID
            target_event: 目标事件类型
            
        Returns:
            List[str]: 需要的前置事件列表（按顺序）
        """
        chain = self.get_chain(character_id)
        event_config = chain.events.get(target_event)
        
        if not event_config:
            return []
        
        # 递归收集所有前置
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
        
        Args:
            character_id: 角色UUID
            current_events: 当前已触发的事件列表
            
        Returns:
            bool: 是否已突破友情墙
        """
        chain = self.get_chain(character_id)
        current_set = set(current_events)
        
        # 满足任一即可
        for breaker in chain.friendzone_breakers:
            if breaker in current_set:
                return True
        
        return False
    
    def get_chain_type(self, character_id: str) -> EventChainType:
        """
        获取角色的事件链类型
        
        Args:
            character_id: 角色UUID
            
        Returns:
            EventChainType
        """
        chain = self.get_chain(character_id)
        return chain.chain_type
    
    def get_missing_prereqs(
        self,
        character_id: str,
        event_type: str,
        current_events: List[str]
    ) -> List[str]:
        """
        获取触发事件缺少的前置条件
        
        Args:
            character_id: 角色UUID
            event_type: 目标事件
            current_events: 当前已触发的事件列表
            
        Returns:
            List[str]: 缺少的前置事件列表
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
