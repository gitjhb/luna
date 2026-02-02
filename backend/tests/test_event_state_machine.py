"""
Event State Machine 单元测试
============================

测试不同角色的事件链路和解锁条件：
- 普通角色: first_date → first_confession → first_nsfw
- 魅魔(phantom): 可跳过约会，直接NSFW
- 高冷角色(yuki): 需要 first_kiss 才能 NSFW

运行: pytest tests/test_event_state_machine.py -v
"""

import pytest
from app.services.event_state_machine import (
    EventStateMachine,
    EventType,
    EventChainType,
    CHARACTER_IDS,
    can_trigger_event,
    get_next_available_events,
    get_required_events_for,
    is_friendzone_broken,
    event_state_machine,
)


# =============================================================================
# 角色ID常量
# =============================================================================

PHANTOM_ID = CHARACTER_IDS["phantom"]  # 魅影
YUKI_ID = CHARACTER_IDS["yuki"]        # Yuki
XIAOMEI_ID = CHARACTER_IDS["xiaomei"]  # 小美 (普通)
LUNA_ID = CHARACTER_IDS["luna"]        # Luna (普通)
MEI_ID = CHARACTER_IDS["mei"]          # 芽衣 (普通)


# =============================================================================
# 基础功能测试
# =============================================================================

class TestEventStateMachineBasics:
    """基础功能测试"""
    
    def test_singleton_exists(self):
        """单例应该存在"""
        assert event_state_machine is not None
        assert isinstance(event_state_machine, EventStateMachine)
    
    def test_get_chain_normal(self):
        """普通角色应该返回 NORMAL 链"""
        chain = event_state_machine.get_chain(XIAOMEI_ID)
        assert chain.chain_type == EventChainType.NORMAL
    
    def test_get_chain_phantom(self):
        """魅影应该返回 PHANTOM 链"""
        chain = event_state_machine.get_chain(PHANTOM_ID)
        assert chain.chain_type == EventChainType.PHANTOM
    
    def test_get_chain_yuki(self):
        """Yuki应该返回 YUKI 链"""
        chain = event_state_machine.get_chain(YUKI_ID)
        assert chain.chain_type == EventChainType.YUKI
    
    def test_unknown_character_uses_default(self):
        """未知角色应该使用默认链 (NORMAL)"""
        chain = event_state_machine.get_chain("unknown-character-id")
        assert chain.chain_type == EventChainType.NORMAL


# =============================================================================
# 普通角色事件链测试
# =============================================================================

class TestNormalChain:
    """普通角色事件链测试 (first_date → first_confession → first_nsfw)"""
    
    @pytest.fixture
    def char_id(self):
        return XIAOMEI_ID
    
    def test_first_chat_always_available(self, char_id):
        """first_chat 应该始终可触发"""
        assert can_trigger_event(char_id, EventType.FIRST_CHAT, [])
    
    def test_first_chat_cannot_repeat(self, char_id):
        """first_chat 不能重复触发"""
        assert not can_trigger_event(
            char_id, EventType.FIRST_CHAT, [EventType.FIRST_CHAT]
        )
    
    def test_first_date_requires_chat(self, char_id):
        """first_date 需要先 first_chat"""
        # 无 first_chat
        assert not can_trigger_event(char_id, EventType.FIRST_DATE, [])
        # 有 first_chat
        assert can_trigger_event(
            char_id, EventType.FIRST_DATE, [EventType.FIRST_CHAT]
        )
    
    def test_first_confession_requires_date(self, char_id):
        """first_confession 需要先 first_date"""
        # 只有 first_chat
        assert not can_trigger_event(
            char_id, EventType.FIRST_CONFESSION, [EventType.FIRST_CHAT]
        )
        # 有 first_date
        assert can_trigger_event(
            char_id, EventType.FIRST_CONFESSION, 
            [EventType.FIRST_CHAT, EventType.FIRST_DATE]
        )
    
    def test_first_nsfw_requires_confession(self, char_id):
        """first_nsfw 需要先 first_confession"""
        # 只有 date
        assert not can_trigger_event(
            char_id, EventType.FIRST_NSFW, 
            [EventType.FIRST_CHAT, EventType.FIRST_DATE]
        )
        # 有 confession
        assert can_trigger_event(
            char_id, EventType.FIRST_NSFW, 
            [EventType.FIRST_CHAT, EventType.FIRST_DATE, EventType.FIRST_CONFESSION]
        )
    
    def test_full_normal_chain(self, char_id):
        """完整普通链路测试"""
        events = []
        
        # Step 1: first_chat
        assert can_trigger_event(char_id, EventType.FIRST_CHAT, events)
        events.append(EventType.FIRST_CHAT)
        
        # Step 2: first_date (需要 first_chat)
        assert can_trigger_event(char_id, EventType.FIRST_DATE, events)
        events.append(EventType.FIRST_DATE)
        
        # Step 3: first_confession (需要 first_date)
        assert can_trigger_event(char_id, EventType.FIRST_CONFESSION, events)
        events.append(EventType.FIRST_CONFESSION)
        
        # Step 4: first_nsfw (需要 first_confession)
        assert can_trigger_event(char_id, EventType.FIRST_NSFW, events)
    
    def test_cannot_skip_to_nsfw(self, char_id):
        """普通角色不能跳过约会/表白直接 NSFW"""
        # 只有 first_chat
        assert not can_trigger_event(
            char_id, EventType.FIRST_NSFW, [EventType.FIRST_CHAT]
        )


# =============================================================================
# 魅魔角色事件链测试
# =============================================================================

class TestPhantomChain:
    """魅魔角色事件链测试 (可跳过约会，直接NSFW)"""
    
    @pytest.fixture
    def char_id(self):
        return PHANTOM_ID
    
    def test_chain_type_is_phantom(self, char_id):
        """应该是 PHANTOM 链"""
        assert event_state_machine.get_chain_type(char_id) == EventChainType.PHANTOM
    
    def test_first_nsfw_only_requires_chat(self, char_id):
        """魅魔 first_nsfw 只需要 first_chat"""
        assert can_trigger_event(
            char_id, EventType.FIRST_NSFW, [EventType.FIRST_CHAT]
        )
    
    def test_can_skip_date_and_confession(self, char_id):
        """魅魔可以跳过约会和表白"""
        events = [EventType.FIRST_CHAT]
        
        # 可以直接 NSFW
        assert can_trigger_event(char_id, EventType.FIRST_NSFW, events)
        
        # 约会是可选的
        assert can_trigger_event(char_id, EventType.FIRST_DATE, events)
        
        # 表白也是可选的
        assert can_trigger_event(char_id, EventType.FIRST_CONFESSION, events)
    
    def test_friendzone_broken_by_chat_only(self, char_id):
        """魅魔聊过就算突破友情墙"""
        assert is_friendzone_broken(char_id, [EventType.FIRST_CHAT])
        assert not is_friendzone_broken(char_id, [])


# =============================================================================
# 高冷角色事件链测试
# =============================================================================

class TestYukiChain:
    """高冷角色事件链测试 (需要 first_kiss 才能 NSFW)"""
    
    @pytest.fixture
    def char_id(self):
        return YUKI_ID
    
    def test_chain_type_is_yuki(self, char_id):
        """应该是 YUKI 链"""
        assert event_state_machine.get_chain_type(char_id) == EventChainType.YUKI
    
    def test_first_kiss_requires_confession(self, char_id):
        """Yuki first_kiss 需要先 first_confession"""
        events = [EventType.FIRST_CHAT, EventType.FIRST_DATE]
        
        # 只有 date 不能 kiss
        assert not can_trigger_event(char_id, EventType.FIRST_KISS, events)
        
        # 有 confession 才能 kiss
        events.append(EventType.FIRST_CONFESSION)
        assert can_trigger_event(char_id, EventType.FIRST_KISS, events)
    
    def test_first_nsfw_requires_kiss(self, char_id):
        """Yuki first_nsfw 需要先 first_kiss"""
        # 只有 confession 不能 NSFW
        events = [
            EventType.FIRST_CHAT, 
            EventType.FIRST_DATE, 
            EventType.FIRST_CONFESSION
        ]
        assert not can_trigger_event(char_id, EventType.FIRST_NSFW, events)
        
        # 有 kiss 才能 NSFW
        events.append(EventType.FIRST_KISS)
        assert can_trigger_event(char_id, EventType.FIRST_NSFW, events)
    
    def test_full_yuki_chain(self, char_id):
        """完整 Yuki 链路测试"""
        events = []
        
        # Step 1: first_chat
        assert can_trigger_event(char_id, EventType.FIRST_CHAT, events)
        events.append(EventType.FIRST_CHAT)
        
        # Step 2: first_date
        assert can_trigger_event(char_id, EventType.FIRST_DATE, events)
        events.append(EventType.FIRST_DATE)
        
        # Step 3: first_confession
        assert can_trigger_event(char_id, EventType.FIRST_CONFESSION, events)
        events.append(EventType.FIRST_CONFESSION)
        
        # Step 4: first_kiss (Yuki 特有)
        assert can_trigger_event(char_id, EventType.FIRST_KISS, events)
        events.append(EventType.FIRST_KISS)
        
        # Step 5: first_nsfw
        assert can_trigger_event(char_id, EventType.FIRST_NSFW, events)


# =============================================================================
# get_next_available_events 测试
# =============================================================================

class TestGetNextAvailableEvents:
    """获取下一步可用事件测试"""
    
    def test_empty_events_returns_first_chat(self):
        """空事件列表应该返回 first_chat"""
        available = get_next_available_events(XIAOMEI_ID, [])
        assert EventType.FIRST_CHAT in available
    
    def test_after_chat_returns_multiple(self):
        """first_chat 后应该有多个可用事件"""
        available = get_next_available_events(
            XIAOMEI_ID, [EventType.FIRST_CHAT]
        )
        assert EventType.FIRST_COMPLIMENT in available
        assert EventType.FIRST_GIFT in available
        assert EventType.FIRST_DATE in available
    
    def test_phantom_nsfw_available_after_chat(self):
        """魅魔 first_chat 后 NSFW 就可用"""
        available = get_next_available_events(
            PHANTOM_ID, [EventType.FIRST_CHAT]
        )
        assert EventType.FIRST_NSFW in available
    
    def test_normal_nsfw_not_available_after_chat(self):
        """普通角色 first_chat 后 NSFW 不可用"""
        available = get_next_available_events(
            XIAOMEI_ID, [EventType.FIRST_CHAT]
        )
        assert EventType.FIRST_NSFW not in available


# =============================================================================
# get_required_events_for 测试
# =============================================================================

class TestGetRequiredEventsFor:
    """获取前置事件链测试"""
    
    def test_first_chat_no_prereqs(self):
        """first_chat 没有前置"""
        required = get_required_events_for(XIAOMEI_ID, EventType.FIRST_CHAT)
        assert required == []
    
    def test_normal_nsfw_prereqs(self):
        """普通角色 NSFW 需要 chat + date + confession"""
        required = get_required_events_for(XIAOMEI_ID, EventType.FIRST_NSFW)
        assert EventType.FIRST_CHAT in required
        assert EventType.FIRST_DATE in required
        assert EventType.FIRST_CONFESSION in required
    
    def test_phantom_nsfw_prereqs(self):
        """魅魔 NSFW 只需要 chat"""
        required = get_required_events_for(PHANTOM_ID, EventType.FIRST_NSFW)
        assert required == [EventType.FIRST_CHAT]
    
    def test_yuki_nsfw_prereqs(self):
        """Yuki NSFW 需要包含 kiss"""
        required = get_required_events_for(YUKI_ID, EventType.FIRST_NSFW)
        assert EventType.FIRST_KISS in required
        assert EventType.FIRST_CONFESSION in required


# =============================================================================
# 友情墙测试
# =============================================================================

class TestFriendzoneWall:
    """友情墙突破条件测试"""
    
    def test_normal_needs_date_or_confession(self):
        """普通角色需要 date 或 confession 突破"""
        # 无事件
        assert not is_friendzone_broken(XIAOMEI_ID, [])
        
        # 只有 chat
        assert not is_friendzone_broken(XIAOMEI_ID, [EventType.FIRST_CHAT])
        
        # 有 date
        assert is_friendzone_broken(
            XIAOMEI_ID, [EventType.FIRST_CHAT, EventType.FIRST_DATE]
        )
        
        # 或者有 confession
        assert is_friendzone_broken(
            XIAOMEI_ID, [EventType.FIRST_CHAT, EventType.FIRST_CONFESSION]
        )
    
    def test_phantom_only_needs_chat(self):
        """魅魔只需要 chat 就突破"""
        assert not is_friendzone_broken(PHANTOM_ID, [])
        assert is_friendzone_broken(PHANTOM_ID, [EventType.FIRST_CHAT])
    
    def test_yuki_needs_date_or_confession(self):
        """Yuki 也需要 date 或 confession 突破"""
        assert not is_friendzone_broken(YUKI_ID, [EventType.FIRST_CHAT])
        assert is_friendzone_broken(
            YUKI_ID, [EventType.FIRST_CHAT, EventType.FIRST_DATE]
        )


# =============================================================================
# get_missing_prereqs 测试
# =============================================================================

class TestGetMissingPrereqs:
    """获取缺少的前置条件测试"""
    
    def test_no_missing_for_first_chat(self):
        """first_chat 没有缺少的前置"""
        missing = event_state_machine.get_missing_prereqs(
            XIAOMEI_ID, EventType.FIRST_CHAT, []
        )
        assert missing == []
    
    def test_missing_chat_for_date(self):
        """first_date 缺少 first_chat"""
        missing = event_state_machine.get_missing_prereqs(
            XIAOMEI_ID, EventType.FIRST_DATE, []
        )
        assert EventType.FIRST_CHAT in missing
    
    def test_missing_confession_for_yuki_nsfw(self):
        """Yuki NSFW 缺少 kiss 当只有 confession 时"""
        missing = event_state_machine.get_missing_prereqs(
            YUKI_ID, EventType.FIRST_NSFW, 
            [EventType.FIRST_CHAT, EventType.FIRST_DATE, EventType.FIRST_CONFESSION]
        )
        assert EventType.FIRST_KISS in missing


# =============================================================================
# 跨角色对比测试
# =============================================================================

class TestCrossCharacterComparison:
    """不同角色的事件链对比测试"""
    
    def test_same_events_different_outcomes(self):
        """相同事件列表，不同角色结果不同"""
        events = [EventType.FIRST_CHAT]
        
        # 魅魔可以 NSFW
        assert can_trigger_event(PHANTOM_ID, EventType.FIRST_NSFW, events)
        
        # 普通角色不能
        assert not can_trigger_event(XIAOMEI_ID, EventType.FIRST_NSFW, events)
        
        # Yuki 也不能
        assert not can_trigger_event(YUKI_ID, EventType.FIRST_NSFW, events)
    
    def test_confession_unlocks_normal_but_not_yuki_nsfw(self):
        """表白后普通角色可以 NSFW，但 Yuki 不行"""
        events = [
            EventType.FIRST_CHAT, 
            EventType.FIRST_DATE, 
            EventType.FIRST_CONFESSION
        ]
        
        # 普通角色可以
        assert can_trigger_event(XIAOMEI_ID, EventType.FIRST_NSFW, events)
        
        # Yuki 还需要 kiss
        assert not can_trigger_event(YUKI_ID, EventType.FIRST_NSFW, events)


# =============================================================================
# 运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
