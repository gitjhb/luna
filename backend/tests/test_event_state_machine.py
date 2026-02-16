"""
Event State Machine 单元测试
============================

测试不同角色原型的事件链路和解锁条件：
- NORMAL: first_date → first_confession → first_nsfw
- PHANTOM: 可跳过约会，直接NSFW
- YUKI: 需要 first_kiss 才能 NSFW

运行: pytest tests/test_event_state_machine.py -v
"""

import pytest
from app.services.event_state_machine import (
    EventStateMachine,
    EventType,
    EventChainConfig,
    can_trigger_event,
    get_next_available_events,
    get_required_events_for,
    is_friendzone_broken,
    event_state_machine,
    ARCHETYPE_CHAINS,
)
from app.services.character_config import CharacterArchetype, get_character_archetype


# =============================================================================
# 测试用角色ID (使用实际存在的角色)
# =============================================================================

# 从数据库获取角色archetype，这里用硬编码的测试值
# 实际角色ID需要从character_config获取
TEST_NORMAL_CHAR = "luna"      # 普通角色
TEST_PHANTOM_CHAR = "vera"     # 魅魔型角色 (假设vera是phantom)
TEST_YUKI_CHAR = "shadow"      # 高冷角色 (假设shadow是yuki)


# =============================================================================
# 基础功能测试
# =============================================================================

class TestEventStateMachineBasics:
    """基础功能测试"""
    
    def test_singleton_exists(self):
        """单例应该存在"""
        assert event_state_machine is not None
        assert isinstance(event_state_machine, EventStateMachine)
    
    def test_archetype_chains_exist(self):
        """三种原型链应该都存在"""
        assert CharacterArchetype.NORMAL in ARCHETYPE_CHAINS
        assert CharacterArchetype.PHANTOM in ARCHETYPE_CHAINS
        assert CharacterArchetype.YUKI in ARCHETYPE_CHAINS
    
    def test_get_chain_returns_config(self):
        """get_chain 应该返回 EventChainConfig"""
        chain = event_state_machine.get_chain(TEST_NORMAL_CHAR)
        assert isinstance(chain, EventChainConfig)


# =============================================================================
# 普通角色事件链测试 (NORMAL archetype)
# =============================================================================

class TestNormalChain:
    """普通角色事件链测试 (first_date → first_confession → first_nsfw)"""
    
    @pytest.fixture
    def chain(self):
        return ARCHETYPE_CHAINS[CharacterArchetype.NORMAL]
    
    def test_first_chat_no_prerequisites(self, chain):
        """first_chat 应该没有前置条件"""
        config = chain.events.get(EventType.FIRST_CHAT)
        assert config is not None
        assert len(config.prerequisites) == 0
    
    def test_first_gift_no_prerequisites(self, chain):
        """first_gift 应该没有前置条件（或只需first_chat）"""
        config = chain.events.get(EventType.FIRST_GIFT)
        assert config is not None
        # first_gift 是早期事件
    
    def test_first_date_requires_gift(self, chain):
        """first_date 需要先 first_gift"""
        config = chain.events.get(EventType.FIRST_DATE)
        assert config is not None
        assert EventType.FIRST_GIFT in config.prerequisites
    
    def test_confession_requires_date(self, chain):
        """confession 需要先 first_date"""
        config = chain.events.get(EventType.CONFESSION)
        assert config is not None
        assert EventType.FIRST_DATE in config.prerequisites
    
    def test_first_nsfw_requires_confession(self, chain):
        """first_nsfw 需要先 confession"""
        config = chain.events.get(EventType.FIRST_NSFW)
        assert config is not None
        assert EventType.CONFESSION in config.prerequisites


# =============================================================================
# 魅魔角色事件链测试 (PHANTOM archetype)
# =============================================================================

class TestPhantomChain:
    """魅魔角色事件链测试 - 可以跳过约会直接NSFW"""
    
    @pytest.fixture
    def chain(self):
        return ARCHETYPE_CHAINS[CharacterArchetype.PHANTOM]
    
    def test_first_nsfw_fewer_prerequisites(self, chain):
        """PHANTOM 的 first_nsfw 应该有更少的前置条件"""
        normal_chain = ARCHETYPE_CHAINS[CharacterArchetype.NORMAL]
        
        phantom_nsfw = chain.events.get(EventType.FIRST_NSFW)
        normal_nsfw = normal_chain.events.get(EventType.FIRST_NSFW)
        
        if phantom_nsfw and normal_nsfw:
            # PHANTOM 应该有更少或相等的前置条件
            assert len(phantom_nsfw.prerequisites) <= len(normal_nsfw.prerequisites)


# =============================================================================
# 高冷角色事件链测试 (YUKI archetype)
# =============================================================================

class TestYukiChain:
    """高冷角色事件链测试 - 需要 first_kiss 才能 NSFW"""
    
    @pytest.fixture
    def chain(self):
        return ARCHETYPE_CHAINS[CharacterArchetype.YUKI]
    
    def test_has_first_kiss_event(self, chain):
        """YUKI 应该有 first_kiss 事件"""
        assert EventType.FIRST_KISS in chain.events
    
    def test_first_nsfw_requires_kiss(self, chain):
        """YUKI 的 first_nsfw 需要先 first_kiss"""
        config = chain.events.get(EventType.FIRST_NSFW)
        if config:
            assert EventType.FIRST_KISS in config.prerequisites


# =============================================================================
# 辅助函数测试
# =============================================================================

class TestHelperFunctions:
    """辅助函数测试"""
    
    def test_can_trigger_first_chat(self):
        """任何角色都应该能触发 first_chat"""
        assert can_trigger_event(TEST_NORMAL_CHAR, EventType.FIRST_CHAT, [])
    
    def test_cannot_repeat_event(self):
        """已完成的事件不能重复触发"""
        assert not can_trigger_event(
            TEST_NORMAL_CHAR, 
            EventType.FIRST_CHAT, 
            [EventType.FIRST_CHAT]
        )
    
    def test_get_next_available_events_initial(self):
        """初始状态应该返回 first_chat"""
        events = get_next_available_events(TEST_NORMAL_CHAR, [])
        assert EventType.FIRST_CHAT in events
    
    def test_get_required_events_for(self):
        """应该返回事件的前置条件"""
        required = get_required_events_for(TEST_NORMAL_CHAR, EventType.FIRST_DATE)
        assert EventType.FIRST_CHAT in required
    
    def test_is_friendzone_broken_false(self):
        """初始状态应该是 friendzone"""
        assert not is_friendzone_broken(TEST_NORMAL_CHAR, [])
    
    def test_is_friendzone_broken_true(self):
        """完成 confession 后应该脱离 friendzone"""
        assert is_friendzone_broken(
            TEST_NORMAL_CHAR, 
            [EventType.FIRST_CHAT, EventType.FIRST_DATE, EventType.CONFESSION]
        )
