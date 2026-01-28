"""
Credit cost calculation utilities
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict


# Pricing configuration
# Base cost: $0.01 per 1000 tokens
# Credit exchange rate: 10 credits = $1
# Therefore: 0.1 credits per 1000 tokens
BASE_COST_PER_1K_TOKENS = Decimal("0.10")

# Tier-based discount multipliers
TIER_DISCOUNTS: Dict[str, Decimal] = {
    "free": Decimal("1.0"),      # No discount
    "premium": Decimal("0.7"),   # 30% discount
    "vip": Decimal("0.5")        # 50% discount
}

# Minimum charge (to prevent abuse of tiny requests)
MIN_CHARGE = Decimal("0.01")


def calculate_chat_cost(tokens_used: int, user_tier: str = "free") -> Decimal:
    """
    Calculate credit cost for a chat completion.
    
    Args:
        tokens_used: Total tokens (prompt + completion)
        user_tier: User's subscription tier ('free', 'premium', 'vip')
    
    Returns:
        Credit cost as Decimal, rounded to 2 decimal places
    
    Examples:
        >>> calculate_chat_cost(1000, "free")
        Decimal('0.10')
        >>> calculate_chat_cost(1000, "premium")
        Decimal('0.07')
        >>> calculate_chat_cost(500, "vip")
        Decimal('0.03')
    """
    if tokens_used <= 0:
        return Decimal("0")
    
    # Calculate base cost
    base_cost = (Decimal(tokens_used) / 1000) * BASE_COST_PER_1K_TOKENS
    
    # Apply tier discount
    discount_multiplier = TIER_DISCOUNTS.get(user_tier, Decimal("1.0"))
    final_cost = base_cost * discount_multiplier
    
    # Apply minimum charge
    final_cost = max(final_cost, MIN_CHARGE)
    
    # Round to 2 decimal places
    return final_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_embedding_cost(num_embeddings: int, user_tier: str = "free") -> Decimal:
    """
    Calculate cost for vector embeddings (for RAG).
    Typically much cheaper than completions.
    
    Args:
        num_embeddings: Number of text chunks to embed
        user_tier: User's subscription tier
    
    Returns:
        Credit cost as Decimal
    """
    # Embedding cost: 0.01 credits per embedding
    base_cost = Decimal(num_embeddings) * Decimal("0.01")
    
    # Apply tier discount
    discount_multiplier = TIER_DISCOUNTS.get(user_tier, Decimal("1.0"))
    final_cost = base_cost * discount_multiplier
    
    return final_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def estimate_tokens_from_text(text: str) -> int:
    """
    Rough estimation of token count from text.
    Rule of thumb: 1 token ≈ 4 characters for English.
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    return max(1, len(text) // 4)


def get_tier_daily_limit(tier: str) -> Decimal:
    """
    Get daily free credit limit for a tier.
    
    Args:
        tier: Subscription tier
    
    Returns:
        Daily credit limit
    """
    limits = {
        "free": Decimal("10.00"),
        "premium": Decimal("100.00"),
        "vip": Decimal("500.00")
    }
    return limits.get(tier, Decimal("10.00"))


def get_tier_rate_limit(tier: str) -> int:
    """
    Get requests per minute limit for a tier.
    
    Args:
        tier: Subscription tier
    
    Returns:
        Requests per minute
    """
    limits = {
        "free": 5,
        "premium": 30,
        "vip": 100
    }
    return limits.get(tier, 5)


def calculate_credit_package_value(package_sku: str) -> Decimal:
    """
    Get credit amount for a purchase package.
    
    Args:
        package_sku: Product SKU (e.g., 'credits_100', 'credits_500')
    
    Returns:
        Credit amount
    """
    packages = {
        "credits_10": Decimal("10.00"),      # $0.99
        "credits_50": Decimal("50.00"),      # $4.99
        "credits_100": Decimal("100.00"),    # $8.99 (10% bonus)
        "credits_500": Decimal("550.00"),    # $39.99 (20% bonus)
        "credits_1000": Decimal("1200.00"),  # $69.99 (30% bonus)
    }
    return packages.get(package_sku, Decimal("0"))


def calculate_subscription_credits(tier: str, period: str = "monthly") -> Decimal:
    """
    Get bonus credits included with subscription.
    
    Args:
        tier: Subscription tier
        period: Billing period ('monthly', 'yearly')
    
    Returns:
        Bonus credits
    """
    if period == "monthly":
        credits = {
            "premium": Decimal("200.00"),   # $9.99/month
            "vip": Decimal("1000.00")       # $29.99/month
        }
    else:  # yearly
        credits = {
            "premium": Decimal("2500.00"),  # $99.99/year (2 months free)
            "vip": Decimal("13000.00")      # $299.99/year (2 months free)
        }
    
    return credits.get(tier, Decimal("0"))
