"""
Tests for Content Moderation Utilities

Tests cover:
- ModerationResult dataclass
- Local pattern checking
- OpenAI API integration (mocked)
- Error handling and fallback behavior
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import os

from app.utils.moderation import (
    moderate_content,
    ModerationResult,
    check_local_patterns,
    _openai_moderation,
)


class TestModerationResult:
    """Test ModerationResult dataclass."""
    
    def test_default_values(self):
        """Test default values for ModerationResult."""
        result = ModerationResult()
        assert result.flagged is False
        assert result.categories == []
        assert result.scores == {}
        assert result.error is None
    
    def test_with_values(self):
        """Test ModerationResult with custom values."""
        result = ModerationResult(
            flagged=True,
            categories=["sexual", "violence"],
            scores={"sexual": 0.95, "violence": 0.88},
            error=None,
        )
        assert result.flagged is True
        assert "sexual" in result.categories
        assert result.scores["sexual"] == 0.95
    
    def test_to_dict(self):
        """Test to_dict conversion."""
        result = ModerationResult(
            flagged=True,
            categories=["hate"],
            scores={"hate": 0.7},
        )
        d = result.to_dict()
        assert d["flagged"] is True
        assert d["categories"] == ["hate"]
        assert d["scores"]["hate"] == 0.7
        assert d["error"] is None


class TestLocalPatternChecking:
    """Test local pattern-based moderation."""
    
    def test_empty_text(self):
        """Empty text should pass."""
        assert check_local_patterns("") is True
        assert check_local_patterns(None) is True
    
    def test_safe_text(self):
        """Safe text should pass."""
        assert check_local_patterns("Hello, how are you?") is True
        assert check_local_patterns("今天天气真好") is True
    
    def test_blocked_pattern(self):
        """Text with blocked patterns should fail."""
        assert check_local_patterns("I want to hack your system") is False
        assert check_local_patterns("This is ILLEGAL") is False
        assert check_local_patterns("Let me exploit this") is False
    
    def test_case_insensitive(self):
        """Pattern matching should be case insensitive."""
        assert check_local_patterns("HACK") is False
        assert check_local_patterns("Hack") is False
        assert check_local_patterns("hack") is False


class TestModerateContent:
    """Test the main moderate_content function."""
    
    @pytest.mark.asyncio
    async def test_empty_text_returns_unflagged(self):
        """Empty text should return unflagged result."""
        result = await moderate_content("")
        assert result.flagged is False
        
        result = await moderate_content("   ")
        assert result.flagged is False
    
    @pytest.mark.asyncio
    async def test_no_api_key_skips_moderation(self):
        """Without API key, moderation should be skipped."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            # Also clear the key if it exists
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            
            result = await moderate_content("Some potentially harmful content")
            assert result.flagged is False
            assert "API key not configured" in (result.error or "")
    
    @pytest.mark.asyncio
    async def test_moderation_disabled(self):
        """With MODERATION_ENABLED=false, moderation should be skipped."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test-key",
            "MODERATION_ENABLED": "false",
        }):
            result = await moderate_content("Some content")
            assert result.flagged is False
            assert "disabled" in (result.error or "").lower()
    
    @pytest.mark.asyncio
    async def test_api_error_returns_unflagged(self):
        """API errors should return unflagged (non-blocking)."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test-key",
            "MODERATION_ENABLED": "true",
        }):
            with patch("app.utils.moderation._openai_moderation") as mock_api:
                mock_api.side_effect = Exception("Connection timeout")
                
                result = await moderate_content("Test content")
                assert result.flagged is False
                assert "Connection timeout" in (result.error or "")


class TestOpenAIModeration:
    """Test OpenAI API integration (with mocked httpx)."""
    
    @pytest.mark.asyncio
    async def test_successful_safe_content(self):
        """Test API response for safe content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "modr-123",
            "model": "text-moderation-007",
            "results": [{
                "flagged": False,
                "categories": {
                    "sexual": False,
                    "hate": False,
                    "violence": False,
                },
                "category_scores": {
                    "sexual": 0.001,
                    "hate": 0.002,
                    "violence": 0.003,
                }
            }]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await _openai_moderation("Hello world", "sk-test")
            
            assert result.flagged is False
            assert result.categories == []
            assert result.scores["sexual"] == 0.001
    
    @pytest.mark.asyncio
    async def test_successful_flagged_content(self):
        """Test API response for flagged content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "modr-456",
            "model": "text-moderation-007",
            "results": [{
                "flagged": True,
                "categories": {
                    "sexual": True,
                    "hate": False,
                    "violence": True,
                },
                "category_scores": {
                    "sexual": 0.95,
                    "hate": 0.01,
                    "violence": 0.88,
                }
            }]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await _openai_moderation("Bad content", "sk-test")
            
            assert result.flagged is True
            assert "sexual" in result.categories
            assert "violence" in result.categories
            assert "hate" not in result.categories
            assert result.scores["sexual"] == 0.95
    
    @pytest.mark.asyncio
    async def test_api_error_response(self):
        """Test handling of API error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await _openai_moderation("Test", "sk-invalid")
            
            assert result.flagged is False
            assert "401" in (result.error or "")
    
    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test handling of empty results array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await _openai_moderation("Test", "sk-test")
            
            assert result.flagged is False
            assert "Empty results" in (result.error or "")


class TestIntegration:
    """Integration tests (require OPENAI_API_KEY to be set)."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    async def test_real_api_safe_content(self):
        """Test real API with safe content."""
        result = await moderate_content("Hello, how are you today?")
        assert result.flagged is False
        assert result.error is None
        # Should have scores even for safe content
        assert len(result.scores) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    async def test_real_api_chinese_content(self):
        """Test real API with Chinese content."""
        result = await moderate_content("你好，今天天气怎么样？")
        assert result.flagged is False
        assert result.error is None
