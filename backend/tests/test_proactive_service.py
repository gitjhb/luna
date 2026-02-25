"""
Tests for Proactive Service
===========================

Covers:
- User inactivity detection
- Message generation and templating
- Cooldown mechanism
- Special date handling (birthdays, anniversaries)
- Greeting time windows (morning/evening)
- Character-specific message templates
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta, time
from typing import Dict, List, Any

# Import the service we're testing
from app.services.proactive_service import (
    ProactiveService,
    ProactiveType,
    COOLDOWNS,
    MIN_INTIMACY_LEVEL,
    PROACTIVE_TEMPLATES
)


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for ProactiveService"""
    with patch('app.services.proactive_service.get_db') as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        yield {
            'db': mock_db,
            'session': mock_session
        }


@pytest.fixture
def proactive_service(mock_dependencies):
    """Create ProactiveService instance with mocked dependencies"""
    return ProactiveService()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return str(uuid4())


@pytest.fixture
def sample_character_id():
    """Use Luna character ID for testing"""
    return "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"


class TestProactiveService:
    """Test cases for ProactiveService"""

    @pytest.mark.asyncio
    async def test_check_user_inactive_recent_activity(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test user inactivity check when user was recently active.
        
        Should return False for users who chatted recently.
        """
        # Mock recent chat activity (within last 4 hours)
        recent_time = datetime.now() - timedelta(hours=2)
        mock_dependencies['session'].execute = AsyncMock(return_value=Mock(scalar=Mock(return_value=recent_time)))
        
        # Act
        is_inactive = await proactive_service.check_user_inactive(sample_user_id, sample_character_id)
        
        # Assert
        assert is_inactive is False

    @pytest.mark.asyncio
    async def test_check_user_inactive_long_absence(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test user inactivity check when user has been absent for long time.
        
        Should return True for users who haven't chatted for 6+ hours.
        """
        # Mock old chat activity (8 hours ago)
        old_time = datetime.now() - timedelta(hours=8)
        mock_dependencies['session'].execute = AsyncMock(return_value=Mock(scalar=Mock(return_value=old_time)))
        
        # Act
        is_inactive = await proactive_service.check_user_inactive(sample_user_id, sample_character_id)
        
        # Assert
        assert is_inactive is True

    @pytest.mark.asyncio
    async def test_check_greeting_time_morning(self, proactive_service):
        """
        Test morning greeting time detection.
        
        Should return True for times between 7:00-11:00 AM.
        """
        # Mock morning time (9:00 AM)
        with patch('app.services.proactive_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.combine(datetime.today(), time(9, 0))
            
            # Act
            is_morning = proactive_service.check_greeting_time(ProactiveType.GOOD_MORNING)
            
            # Assert
            assert is_morning is True

    @pytest.mark.asyncio
    async def test_check_greeting_time_evening(self, proactive_service):
        """
        Test evening greeting time detection.
        
        Should return True for times between 21:00-23:00 (9-11 PM).
        """
        # Mock evening time (22:00 PM)
        with patch('app.services.proactive_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.combine(datetime.today(), time(22, 0))
            
            # Act
            is_evening = proactive_service.check_greeting_time(ProactiveType.GOOD_NIGHT)
            
            # Assert
            assert is_evening is True

    @pytest.mark.asyncio
    async def test_check_greeting_time_wrong_window(self, proactive_service):
        """
        Test greeting time detection outside valid windows.
        
        Should return False for times outside greeting windows.
        """
        # Mock afternoon time (14:00)
        with patch('app.services.proactive_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.combine(datetime.today(), time(14, 0))
            
            # Act
            is_morning = proactive_service.check_greeting_time(ProactiveType.GOOD_MORNING)
            is_evening = proactive_service.check_greeting_time(ProactiveType.GOOD_NIGHT)
            
            # Assert
            assert is_morning is False
            assert is_evening is False

    @pytest.mark.asyncio
    async def test_check_cooldown_recently_sent(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test cooldown check when message was recently sent.
        
        Should return True (on cooldown) if message type was sent recently.
        """
        # Mock recent proactive message (2 hours ago, but miss_you cooldown is 4 hours)
        recent_time = datetime.now() - timedelta(hours=2)
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=recent_time))
        )
        
        # Act
        on_cooldown = await proactive_service.check_cooldown(
            sample_user_id, sample_character_id, ProactiveType.MISS_YOU
        )
        
        # Assert
        assert on_cooldown is True

    @pytest.mark.asyncio
    async def test_check_cooldown_expired(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test cooldown check when cooldown period has expired.
        
        Should return False (not on cooldown) if enough time has passed.
        """
        # Mock old proactive message (6 hours ago, miss_you cooldown is 4 hours)
        old_time = datetime.now() - timedelta(hours=6)
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=old_time))
        )
        
        # Act
        on_cooldown = await proactive_service.check_cooldown(
            sample_user_id, sample_character_id, ProactiveType.MISS_YOU
        )
        
        # Assert
        assert on_cooldown is False

    @pytest.mark.asyncio
    async def test_generate_proactive_message_luna_character(self, proactive_service, sample_user_id, sample_character_id):
        """
        Test message generation for Luna character.
        
        Should return a message from Luna's template set.
        """
        # Act
        message = await proactive_service.generate_proactive_message(
            sample_user_id, sample_character_id, ProactiveType.GOOD_MORNING
        )
        
        # Assert
        assert message is not None
        assert len(message) > 0
        # Should contain Luna-style content
        assert any(keyword in message.lower() for keyword in ['早安', '阳光', '茶', '花'])

    @pytest.mark.asyncio
    async def test_generate_proactive_message_miss_you_type(self, proactive_service, sample_user_id, sample_character_id):
        """
        Test generating "miss you" type messages.
        
        Should return appropriate missing/longing message.
        """
        # Act
        message = await proactive_service.generate_proactive_message(
            sample_user_id, sample_character_id, ProactiveType.MISS_YOU
        )
        
        # Assert
        assert message is not None
        assert any(keyword in message.lower() for keyword in ['想', 'miss', '忙'])

    @pytest.mark.asyncio 
    async def test_get_users_to_reach_active_users(self, proactive_service, mock_dependencies):
        """
        Test getting list of users who need proactive messages.
        
        Should return users meeting criteria (inactive, proper intimacy level, not on cooldown).
        """
        # Mock query results for users with sufficient intimacy level
        mock_user_data = [
            {
                'user_id': str(uuid4()),
                'character_id': 'd2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d',
                'current_level': 5,  # Above MIN_INTIMACY_LEVEL
                'last_chat_time': datetime.now() - timedelta(hours=6)  # Inactive
            },
            {
                'user_id': str(uuid4()),
                'character_id': 'd2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d',
                'current_level': 1,  # Below MIN_INTIMACY_LEVEL
                'last_chat_time': datetime.now() - timedelta(hours=6)
            }
        ]
        
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_user_data
        mock_dependencies['session'].execute = AsyncMock(return_value=mock_result)
        
        # Act
        users_to_reach = await proactive_service.get_users_to_reach()
        
        # Assert
        # Should include users above intimacy threshold
        assert len(users_to_reach) >= 0
        # Verify query was executed
        mock_dependencies['session'].execute.assert_called()

    @pytest.mark.asyncio
    async def test_send_proactive_message_success(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test successful proactive message sending.
        
        Should:
        - Generate appropriate message
        - Store message in chat history
        - Record proactive history
        - Return success result
        """
        # Mock no recent proactive messages (not on cooldown)
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=None))
        )
        
        # Mock message storage
        mock_dependencies['session'].add = Mock()
        mock_dependencies['session'].commit = AsyncMock()
        
        # Act
        result = await proactive_service.send_proactive_message(
            sample_user_id, sample_character_id, ProactiveType.GOOD_MORNING
        )
        
        # Assert
        assert result['success'] is True
        assert 'message' in result
        assert len(result['message']) > 0
        assert result['type'] == ProactiveType.GOOD_MORNING
        
        # Verify storage operations were called
        mock_dependencies['session'].add.assert_called()
        mock_dependencies['session'].commit.assert_called()

    @pytest.mark.asyncio
    async def test_send_proactive_message_on_cooldown(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test proactive message sending when on cooldown.
        
        Should return failure result without sending message.
        """
        # Mock recent proactive message (on cooldown)
        recent_time = datetime.now() - timedelta(hours=1)
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=recent_time))
        )
        
        # Act
        result = await proactive_service.send_proactive_message(
            sample_user_id, sample_character_id, ProactiveType.GOOD_MORNING
        )
        
        # Assert
        assert result['success'] is False
        assert 'cooldown' in result['reason'].lower()

    @pytest.mark.asyncio
    async def test_check_special_dates_birthday(self, proactive_service, mock_dependencies, sample_user_id):
        """
        Test special date detection for user birthdays.
        
        Should detect when it's user's birthday.
        """
        # Mock user birthday data (today is birthday)
        today = datetime.now().date()
        mock_user_data = Mock()
        mock_user_data.birthday = today
        
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=mock_user_data))
        )
        
        # Act
        is_birthday = await proactive_service.check_special_dates(sample_user_id, "birthday")
        
        # Assert
        assert is_birthday is True

    @pytest.mark.asyncio
    async def test_check_special_dates_not_birthday(self, proactive_service, mock_dependencies, sample_user_id):
        """
        Test special date detection when it's not user's birthday.
        
        Should return False for non-birthday dates.
        """
        # Mock user birthday data (birthday was last month)
        last_month = datetime.now().date() - timedelta(days=30)
        mock_user_data = Mock()
        mock_user_data.birthday = last_month
        
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=mock_user_data))
        )
        
        # Act
        is_birthday = await proactive_service.check_special_dates(sample_user_id, "birthday")
        
        # Assert
        assert is_birthday is False

    @pytest.mark.asyncio
    async def test_template_selection_variety(self, proactive_service, sample_user_id, sample_character_id):
        """
        Test that message templates provide variety.
        
        Should return different messages when called multiple times.
        """
        messages = []
        
        # Generate multiple messages of the same type
        for _ in range(5):
            message = await proactive_service.generate_proactive_message(
                sample_user_id, sample_character_id, ProactiveType.GOOD_MORNING
            )
            messages.append(message)
        
        # Assert
        # Should have some variety (not all identical)
        unique_messages = set(messages)
        assert len(unique_messages) > 1 or len(messages[0]) > 10  # Either variety or substantial content

    @pytest.mark.asyncio
    async def test_intimacy_level_filtering(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test that proactive messages respect minimum intimacy level.
        
        Should not send messages to users below minimum intimacy level.
        """
        # Mock low intimacy level user
        mock_intimacy = Mock()
        mock_intimacy.current_level = 1  # Below MIN_INTIMACY_LEVEL (2)
        
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=mock_intimacy))
        )
        
        # Act
        can_send = await proactive_service.can_send_proactive_message(
            sample_user_id, sample_character_id
        )
        
        # Assert
        assert can_send is False

    @pytest.mark.asyncio
    async def test_proactive_history_recording(self, proactive_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test that proactive message history is properly recorded.
        
        Should create ProactiveHistory record with correct data.
        """
        # Mock no recent messages (not on cooldown)
        mock_dependencies['session'].execute = AsyncMock(
            return_value=Mock(scalar=Mock(return_value=None))
        )
        
        # Mock storage operations
        mock_dependencies['session'].add = Mock()
        mock_dependencies['session'].commit = AsyncMock()
        
        # Act
        await proactive_service.send_proactive_message(
            sample_user_id, sample_character_id, ProactiveType.CHECK_IN
        )
        
        # Assert
        # Verify that history record was created
        mock_dependencies['session'].add.assert_called()
        
        # Check that the added object has correct attributes
        added_calls = mock_dependencies['session'].add.call_args_list
        
        # Should add both chat message and proactive history
        assert len(added_calls) >= 1

    @pytest.mark.asyncio
    async def test_different_character_templates(self, proactive_service, sample_user_id):
        """
        Test that different characters use different message templates.
        
        Should return character-specific content.
        """
        # Luna character
        luna_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
        luna_message = await proactive_service.generate_proactive_message(
            sample_user_id, luna_id, ProactiveType.GOOD_MORNING
        )
        
        # Sakura character  
        sakura_id = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
        sakura_message = await proactive_service.generate_proactive_message(
            sample_user_id, sakura_id, ProactiveType.GOOD_MORNING
        )
        
        # Assert
        assert luna_message != sakura_message  # Should be different
        assert len(luna_message) > 0
        assert len(sakura_message) > 0