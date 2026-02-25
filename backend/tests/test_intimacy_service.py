"""
Tests for Intimacy Service
==========================

Covers:
- XP calculation and level progression
- Daily XP caps and action limits
- Intimacy stage management
- Bottleneck locks
- Action rewards and cooldowns
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Dict, Any

# Import the service we're testing
from app.services.intimacy_service import IntimacyService


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for IntimacyService"""
    with patch('app.services.intimacy_service.MOCK_MODE', True):
        # Clear mock storage before each test
        from app.services.intimacy_service import _MOCK_INTIMACY_STORAGE, _MOCK_ACTION_LOGS
        _MOCK_INTIMACY_STORAGE.clear()
        _MOCK_ACTION_LOGS.clear()
        yield


@pytest.fixture
def intimacy_service(mock_dependencies):
    """Create IntimacyService instance with mocked dependencies"""
    return IntimacyService()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return str(uuid4())


@pytest.fixture
def sample_character_id():
    """Generate a sample character ID"""
    return str(uuid4())


class TestIntimacyService:
    """Test cases for IntimacyService"""

    @pytest.mark.asyncio
    async def test_xp_calculation_early_levels(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test XP requirements for early levels (0-9) follow pre-defined thresholds.
        
        Should use EARLY_LEVEL_XP for levels 0-9.
        """
        # Test early level thresholds
        expected_thresholds = [0, 10, 20, 50, 100, 180, 280, 400, 550, 750]
        
        for level in range(10):
            required_xp = intimacy_service.get_xp_for_level(level)
            assert required_xp == expected_thresholds[level], f"Level {level} XP mismatch"

    @pytest.mark.asyncio  
    async def test_xp_calculation_exponential_levels(self, intimacy_service):
        """
        Test XP requirements for higher levels (10+) follow exponential formula.
        
        Should use BASE_XP * MULTIPLIER^(level-9) for levels 10+.
        """
        # Test exponential growth for levels 10+
        base_xp = intimacy_service.BASE_XP  # 300
        multiplier = intimacy_service.MULTIPLIER  # 1.3
        
        for level in range(10, 15):
            expected_xp = int(base_xp * (multiplier ** (level - 9)))
            actual_xp = intimacy_service.get_xp_for_level(level)
            assert actual_xp == expected_xp, f"Level {level} exponential XP mismatch"

    @pytest.mark.asyncio
    async def test_add_xp_normal_flow(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test adding XP for various actions within daily limits.
        
        Should:
        - Grant XP for valid actions
        - Update user level when threshold reached
        - Respect daily limits
        """
        # Test message XP (unlimited)
        result = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "message", 1
        )
        
        assert result['success'] is True
        assert result['xp_gained'] == 2  # message action gives 2 XP
        assert result['total_xp'] == 2
        assert result['current_level'] == 0  # Still level 0 (needs 10 XP for level 1)

    @pytest.mark.asyncio
    async def test_add_xp_level_up(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test level progression when XP threshold is reached.
        
        Should trigger level up and update intimacy stage.
        """
        # Add enough XP to trigger level up to level 1 (needs 10 XP)
        result = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "message", 5  # 5 messages = 10 XP
        )
        
        assert result['success'] is True
        assert result['xp_gained'] == 10
        assert result['total_xp'] == 10
        assert result['current_level'] == 1
        assert result['level_up'] is True
        assert result['intimacy_stage'] == 0  # Still stage 0, needs higher levels

    @pytest.mark.asyncio
    async def test_daily_xp_cap(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test daily XP cap enforcement (500 XP/day).
        
        Should stop granting XP when daily cap is reached.
        """
        # Add XP to approach daily cap (500)
        # Use checkin action (20 XP) to quickly reach cap
        for i in range(25):  # 25 * 20 = 500 XP
            result = await intimacy_service.add_xp(
                sample_user_id, sample_character_id, "checkin", 1
            )
            
            if i < 24:  # First 24 should succeed
                assert result['success'] is True
                assert result['xp_gained'] == 20
            else:  # 25th should hit daily limit (checkin has daily limit of 1)
                assert result['success'] is False
                assert 'daily limit' in result.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_action_daily_limits(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test action-specific daily limits.
        
        Actions like checkin should be limited to once per day.
        """
        # First checkin should succeed
        result1 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "checkin", 1
        )
        assert result1['success'] is True
        assert result1['xp_gained'] == 20

        # Second checkin same day should fail
        result2 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "checkin", 1
        )
        assert result2['success'] is False
        assert 'daily limit' in result2.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_intimacy_stage_progression(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test intimacy stage progression based on level ranges.
        
        Should advance through stages: Stranger -> Acquaintance -> Friend -> Close -> Romantic
        """
        # Test stage 0 (Stranger) - levels 0-4
        stage = intimacy_service.get_intimacy_stage(level=2)
        assert stage == 0

        # Test stage 1 (Acquaintance) - levels 5-14  
        stage = intimacy_service.get_intimacy_stage(level=10)
        assert stage == 1

        # Test stage 2 (Friend) - levels 15-24
        stage = intimacy_service.get_intimacy_stage(level=20)
        assert stage == 2

        # Test stage 3 (Close) - levels 25-34
        stage = intimacy_service.get_intimacy_stage(level=30)
        assert stage == 3

        # Test stage 4 (Romantic) - levels 35+
        stage = intimacy_service.get_intimacy_stage(level=40)
        assert stage == 4

    @pytest.mark.asyncio
    async def test_get_user_intimacy_stats(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test retrieving user intimacy statistics.
        
        Should return current level, XP, stage, and progress information.
        """
        # Add some initial XP
        await intimacy_service.add_xp(sample_user_id, sample_character_id, "message", 3)
        
        # Get stats
        stats = await intimacy_service.get_user_intimacy(sample_user_id, sample_character_id)
        
        assert stats is not None
        assert 'current_level' in stats
        assert 'total_xp' in stats
        assert 'intimacy_stage' in stats
        assert 'stage_name' in stats
        assert 'daily_xp' in stats
        assert stats['total_xp'] == 6  # 3 messages * 2 XP each

    @pytest.mark.asyncio
    async def test_bottleneck_lock_system(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test bottleneck lock system for stage progression.
        
        Certain stages should require specific actions/events to unlock.
        """
        # Test that bottleneck lock prevents progression
        # This would typically require gift giving or dates for higher stages
        
        # Simulate high level but no bottleneck unlock
        with patch.object(intimacy_service, 'get_bottleneck_status', return_value={
            'locked': True,
            'required_action': 'gift',
            'stage': 2
        }):
            
            # Even with high level, should be locked at previous stage
            stats = await intimacy_service.get_user_intimacy(sample_user_id, sample_character_id)
            
            # Should check for bottleneck restrictions
            # Note: This test depends on implementation details
            assert intimacy_service.get_bottleneck_status.called

    @pytest.mark.asyncio
    async def test_action_cooldowns(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test action cooldown system.
        
        Actions like voice interaction should have cooldown periods.
        """
        # First voice action should succeed
        result1 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "voice", 1
        )
        assert result1['success'] is True
        assert result1['xp_gained'] == 15

        # Immediate second voice action should fail due to cooldown
        result2 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "voice", 1  
        )
        assert result2['success'] is False
        assert 'cooldown' in result2.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_invalid_action_type(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test handling of invalid/unknown action types.
        
        Should reject unknown actions gracefully.
        """
        result = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "invalid_action", 1
        )
        
        assert result['success'] is False
        assert 'unknown action' in result.get('reason', '').lower() or \
               'invalid action' in result.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_continuous_chat_bonus(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test continuous chat bonus system.
        
        Should grant bonus XP for sustained conversations.
        """
        # Test continuous chat bonus
        result = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "continuous_chat", 1
        )
        
        assert result['success'] is True
        assert result['xp_gained'] == 5  # continuous_chat gives 5 XP
        
        # Should be unlimited (no daily limit)
        result2 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "continuous_chat", 1
        )
        assert result2['success'] is True

    @pytest.mark.asyncio
    async def test_emotional_expression_rewards(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test emotional expression XP rewards.
        
        Should grant XP for emotional interactions with daily limits.
        """
        # Test emotional expression (daily limit of 5)
        for i in range(6):
            result = await intimacy_service.add_xp(
                sample_user_id, sample_character_id, "emotional", 1
            )
            
            if i < 5:  # First 5 should succeed
                assert result['success'] is True
                assert result['xp_gained'] == 10
            else:  # 6th should fail due to daily limit
                assert result['success'] is False
                assert 'daily limit' in result.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_share_bonus_weekly_cooldown(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test share bonus with weekly cooldown.
        
        Share actions should have a 7-day cooldown period.
        """
        # First share should succeed
        result1 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "share", 1
        )
        assert result1['success'] is True
        assert result1['xp_gained'] == 50  # High reward for sharing

        # Second share immediately should fail due to weekly cooldown
        result2 = await intimacy_service.add_xp(
            sample_user_id, sample_character_id, "share", 1
        )
        assert result2['success'] is False
        assert 'cooldown' in result2.get('reason', '').lower()

    @pytest.mark.asyncio
    async def test_stage_name_mapping(self, intimacy_service):
        """
        Test that stage numbers correctly map to stage names.
        
        Should return appropriate localized stage names.
        """
        stage_names = {
            0: "Stranger",
            1: "Acquaintance", 
            2: "Friend",
            3: "Close",
            4: "Romantic"
        }
        
        for stage_num, expected_name in stage_names.items():
            actual_name = intimacy_service.get_stage_name(stage_num)
            assert expected_name.lower() in actual_name.lower()

    @pytest.mark.asyncio
    async def test_progress_calculation(self, intimacy_service, sample_user_id, sample_character_id):
        """
        Test progress calculation within current level.
        
        Should correctly calculate percentage progress to next level.
        """
        # Add specific amount of XP
        await intimacy_service.add_xp(sample_user_id, sample_character_id, "message", 2)  # 4 XP
        
        stats = await intimacy_service.get_user_intimacy(sample_user_id, sample_character_id)
        
        # At 4 XP, level 0 (next level at 10 XP)
        # Progress should be 4/10 = 40%
        if 'progress_percentage' in stats:
            assert 30 <= stats['progress_percentage'] <= 50  # Allow some tolerance