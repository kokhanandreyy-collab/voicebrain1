from slowapi import Limiter
from slowapi.util import get_remote_address
from infrastructure.config import settings
from fastapi import Request

def get_user_or_ip_identifier(request: Request) -> str:
    """
    Rate limit key generator: 
    Prioritizes user_id from request.state (set by AuthMiddleware), 
    falls back to remote IP address.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)

# Initialize Limiter with Redis storage
limiter = Limiter(
    key_func=get_user_or_ip_identifier,
    storage_uri=settings.REDIS_URL,
    default_limits=["200 per minute"]
)
