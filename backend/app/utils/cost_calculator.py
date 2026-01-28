"""
Credit Cost Calculator
"""

from decimal import Decimal


def calculate_chat_cost(tokens_used: int, tier: str = "free") -> Decimal:
    """
    Calculate credit cost for a chat completion.
    
    Args:
        tokens_used: Number of tokens used
        tier: User subscription tier (free, premium, vip)
    
    Returns:
        Cost in credits (Decimal)
    """
    # Base cost: 0.1 credits per 1000 tokens
    base_cost = Decimal(str(tokens_used)) / Decimal("1000") * Decimal("0.1")

    # Tier discounts
    discounts = {
        "free": Decimal("1.0"),      # No discount
        "premium": Decimal("0.7"),   # 30% off
        "vip": Decimal("0.5"),       # 50% off
    }

    discount = discounts.get(tier, Decimal("1.0"))
    final_cost = base_cost * discount

    # Minimum cost: 0.01 credits
    return max(final_cost, Decimal("0.01"))


def calculate_tts_cost(characters: int, tier: str = "free") -> Decimal:
    """Calculate credit cost for TTS"""
    # Base: 5 credits per request
    base_cost = Decimal("5.0")

    discounts = {"free": Decimal("1.0"), "premium": Decimal("0.7"), "vip": Decimal("0.5")}
    discount = discounts.get(tier, Decimal("1.0"))

    return base_cost * discount


def calculate_image_cost(tier: str = "free") -> Decimal:
    """Calculate credit cost for image generation"""
    # Base: 10 credits per image
    base_cost = Decimal("10.0")

    discounts = {"free": Decimal("1.0"), "premium": Decimal("0.7"), "vip": Decimal("0.5")}
    discount = discounts.get(tier, Decimal("1.0"))

    return base_cost * discount
