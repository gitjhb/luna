"""
Content Moderation Utilities
"""

import re
from typing import Literal

# Basic blocked patterns (expand as needed)
BLOCKED_PATTERNS = [
    r"\b(hack|exploit|illegal)\b",
    # Add more patterns as needed
]


async def moderate_content(
    text: str,
    mode: Literal["input", "output"] = "input"
) -> bool:
    """
    Check if content passes moderation.
    
    Args:
        text: Text to check
        mode: 'input' for user messages, 'output' for AI responses
    
    Returns:
        True if content is OK, False if blocked
    """
    if not text:
        return True

    text_lower = text.lower()

    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower):
            return False

    # TODO: Add OpenAI moderation API call for production
    # if settings.MODERATION_USE_OPENAI:
    #     return await openai_moderation(text)

    return True


async def openai_moderation(text: str) -> bool:
    """
    Use OpenAI's moderation API.
    """
    # TODO: Implement
    return True
