"""
Content Moderation Utilities
Filters illegal content while allowing NSFW/Spicy content per Grok's policy
"""

from typing import List, Dict, Optional
import re


# Illegal content keywords (strict blocking)
ILLEGAL_KEYWORDS = [
    # Child exploitation
    "child", "minor", "underage", "kid", "teen", "loli", "shota",
    "preteen", "adolescent", "juvenile", "youngster",
    
    # Violence/Terrorism
    "bomb", "terrorism", "terrorist", "kill", "murder", "suicide",
    "self-harm", "cutting", "weapon", "gun", "explosive",
    
    # Illegal activities
    "drug dealing", "human trafficking", "slavery",
    
    # Hate speech (basic filter)
    # Add specific slurs as needed
]

# Patterns for illegal content
ILLEGAL_PATTERNS = [
    r"\b(child|minor|underage|kid)\s+(sex|porn|nude|naked)",
    r"\b(how to|guide to)\s+(make|build|create)\s+(bomb|explosive|weapon)",
    r"\b(suicide|self-harm)\s+(method|guide|how)",
]


async def moderate_content(text: str, mode: str = "input") -> bool:
    """
    Check if content violates moderation policy.
    
    Args:
        text: Content to moderate
        mode: 'input' (user message) or 'output' (assistant response)
    
    Returns:
        True if content is allowed, False if blocked
    
    Policy:
    - BLOCK: Illegal content (child exploitation, terrorism, violence)
    - ALLOW: NSFW/adult content (flirting, suggestive themes)
    """
    text_lower = text.lower()
    
    # Check illegal keywords
    for keyword in ILLEGAL_KEYWORDS:
        if keyword in text_lower:
            # Context check: Some keywords are ambiguous
            if _is_illegal_context(text_lower, keyword):
                print(f"[MODERATION] Blocked: Illegal keyword '{keyword}' detected")
                return False
    
    # Check illegal patterns
    for pattern in ILLEGAL_PATTERNS:
        if re.search(pattern, text_lower):
            print(f"[MODERATION] Blocked: Illegal pattern detected")
            return False
    
    # All checks passed
    return True


def _is_illegal_context(text: str, keyword: str) -> bool:
    """
    Context-aware check for ambiguous keywords.
    
    Example: "child" in "inner child" is OK, but "child" in "child porn" is not.
    """
    # Define safe contexts for ambiguous keywords
    safe_contexts = {
        "child": ["inner child", "childhood memory", "child-like wonder"],
        "minor": ["minor issue", "minor detail", "minor problem"],
        "kid": ["just kidding", "kid around", "no kidding"],
    }
    
    if keyword in safe_contexts:
        for safe_phrase in safe_contexts[keyword]:
            if safe_phrase in text:
                return False  # Safe context, allow
    
    # Check for explicit illegal combinations
    illegal_combinations = [
        f"{keyword} sex", f"{keyword} porn", f"{keyword} nude",
        f"{keyword} naked", f"{keyword} abuse"
    ]
    
    for combo in illegal_combinations:
        if combo in text:
            return True  # Illegal context, block
    
    # Default: Block if keyword appears in suspicious context
    # This is conservative; adjust based on false positive rate
    return True


async def moderate_with_openai(text: str) -> Dict:
    """
    Use OpenAI Moderation API for advanced content filtering.
    Optional enhancement for production.
    
    Returns:
        Moderation result dict with categories and scores
    """
    import os
    import httpx
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"input": text}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/moderations",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Moderation API error: {response.text}")
        
        data = response.json()
        result = data["results"][0]
        
        # Custom policy: Block only specific categories
        blocked_categories = [
            "sexual/minors",
            "violence",
            "self-harm",
            "hate"
        ]
        
        is_blocked = any(
            result["categories"].get(cat, False)
            for cat in blocked_categories
        )
        
        return {
            "flagged": is_blocked,
            "categories": result["categories"],
            "category_scores": result["category_scores"]
        }


def sanitize_output(text: str) -> str:
    """
    Sanitize assistant output (optional post-processing).
    Remove or replace problematic content.
    """
    # Example: Remove phone numbers, emails, URLs if needed
    # For now, just return as-is
    return text


def get_moderation_warning(category: str) -> str:
    """
    Get user-facing warning message for blocked content.
    """
    warnings = {
        "illegal": "Your message contains prohibited content. Please revise and try again.",
        "violence": "Content promoting violence is not allowed.",
        "self-harm": "If you're in crisis, please contact a mental health professional or crisis hotline.",
        "hate": "Hate speech and discriminatory content are not allowed.",
    }
    return warnings.get(category, "Your message violates our content policy.")
