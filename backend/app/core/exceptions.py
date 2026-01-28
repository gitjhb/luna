"""
Custom exceptions for AI Companion Platform
"""

from decimal import Decimal
from typing import Optional


class AppException(Exception):
    """Base exception for all application errors"""
    pass


class InsufficientCreditsError(AppException):
    """Raised when user doesn't have enough credits"""
    
    def __init__(
        self, 
        message: str, 
        current_balance: Decimal, 
        required_amount: Decimal
    ):
        super().__init__(message)
        self.current_balance = current_balance
        self.required_amount = required_amount


class RateLimitExceededError(AppException):
    """Raised when user exceeds rate limit"""
    
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after  # seconds


class SubscriptionRequiredError(AppException):
    """Raised when feature requires subscription"""
    
    def __init__(self, message: str, required_tier: str):
        super().__init__(message)
        self.required_tier = required_tier


class AuthenticationError(AppException):
    """Raised when authentication fails"""
    pass


class CharacterNotFoundError(AppException):
    """Raised when character doesn't exist"""
    pass


class SessionNotFoundError(AppException):
    """Raised when chat session doesn't exist"""
    pass


class ContentModerationError(AppException):
    """Raised when content violates moderation policy"""
    
    def __init__(self, message: str, flagged_content: Optional[str] = None):
        super().__init__(message)
        self.flagged_content = flagged_content


class VectorDBError(AppException):
    """Raised when vector database operation fails"""
    pass


class LLMServiceError(AppException):
    """Raised when LLM API call fails"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
