from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import HTTPException
from config import get_settings

settings = get_settings()

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request, exc):
    """Custom handler for rate limit exceeded"""
    return HTTPException(status_code=429, detail="Rate limit exceeded")


class RateLimitService:
    """Service for managing rate limits"""

    @staticmethod
    def get_limiter():
        """Get limiter instance for middleware"""
        return limiter

    @staticmethod
    def get_login_limit() -> str:
        """Get login rate limit string for decorator"""
        return f"{settings.LOGIN_RATE_LIMIT}/minute"
