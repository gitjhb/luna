"""
Content Moderation Utilities

Uses OpenAI Moderation API for content safety checks.
Non-blocking: if API key is missing or API fails, content is allowed through.
"""

import os
import re
import logging
from typing import Literal, Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Basic blocked patterns (local fallback, expand as needed)
BLOCKED_PATTERNS = [
    r"\b(hack|exploit|illegal)\b",
    # Add more patterns as needed
]


@dataclass
class ModerationResult:
    """
    Result from content moderation check.
    
    Attributes:
        flagged: True if content was flagged as potentially harmful
        categories: List of triggered category names (e.g., ["sexual", "violence"])
        scores: Dict of category name -> confidence score (0.0 to 1.0)
        error: Error message if moderation API call failed (None if successful)
    """
    flagged: bool = False
    categories: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "flagged": self.flagged,
            "categories": self.categories,
            "scores": self.scores,
            "error": self.error,
        }


async def moderate_content(
    text: str,
    mode: Literal["input", "output"] = "input"
) -> ModerationResult:
    """
    Check if content passes moderation using OpenAI Moderation API.
    
    This function is NON-BLOCKING:
    - If OPENAI_API_KEY is not set, returns unflagged result
    - If API call fails, logs error and returns unflagged result
    - Only flags content if API explicitly indicates harmful content
    
    Args:
        text: Text to check
        mode: 'input' for user messages, 'output' for AI responses
    
    Returns:
        ModerationResult with flagged status, categories, and scores
    """
    if not text or not text.strip():
        return ModerationResult(flagged=False)
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.debug("OPENAI_API_KEY not set, skipping moderation API call")
        return ModerationResult(flagged=False, error="API key not configured")
    
    # Check if moderation is enabled (default: True if API key exists)
    moderation_enabled = os.getenv("MODERATION_ENABLED", "true").lower() == "true"
    if not moderation_enabled:
        logger.debug("Moderation disabled via MODERATION_ENABLED=false")
        return ModerationResult(flagged=False, error="Moderation disabled")
    
    # Call OpenAI Moderation API
    try:
        return await _openai_moderation(text, api_key)
    except Exception as e:
        logger.warning(f"Moderation API call failed: {e}")
        return ModerationResult(flagged=False, error=str(e))


async def _openai_moderation(text: str, api_key: str) -> ModerationResult:
    """
    Call OpenAI's Moderation API.
    
    API Reference: https://platform.openai.com/docs/api-reference/moderations
    
    Args:
        text: Text to moderate
        api_key: OpenAI API key
    
    Returns:
        ModerationResult with flagged status and category details
    """
    import httpx
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/moderations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"input": text}
        )
        
        if response.status_code != 200:
            error_msg = f"OpenAI API returned {response.status_code}: {response.text}"
            logger.warning(error_msg)
            return ModerationResult(flagged=False, error=error_msg)
        
        data = response.json()
        
        # Parse response
        if not data.get("results"):
            return ModerationResult(flagged=False, error="Empty results from API")
        
        result = data["results"][0]
        flagged = result.get("flagged", False)
        
        # Extract flagged categories
        categories = []
        category_flags = result.get("categories", {})
        for category, is_flagged in category_flags.items():
            if is_flagged:
                categories.append(category)
        
        # Extract category scores
        scores = result.get("category_scores", {})
        # Round scores for cleaner output
        scores = {k: round(v, 4) for k, v in scores.items()}
        
        if flagged:
            logger.info(f"Content flagged - categories: {categories}")
        
        return ModerationResult(
            flagged=flagged,
            categories=categories,
            scores=scores,
        )


def check_local_patterns(text: str) -> bool:
    """
    Check text against local blocked patterns (fast, offline fallback).
    
    Args:
        text: Text to check
    
    Returns:
        True if content is OK, False if blocked
    """
    if not text:
        return True
    
    text_lower = text.lower()
    
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower):
            return False
    
    return True


# Legacy function for backward compatibility
async def moderate_content_legacy(
    text: str,
    mode: Literal["input", "output"] = "input"
) -> bool:
    """
    Legacy moderation function that returns True if content is OK.
    
    Deprecated: Use moderate_content() instead for detailed results.
    
    Returns:
        True if content is OK, False if blocked
    """
    result = await moderate_content(text, mode)
    return not result.flagged
