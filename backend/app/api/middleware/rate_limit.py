from slowapi.middleware import SlowAPIMiddleware as _SlowAPIMiddleware
from infrastructure.rate_limit import limiter

class RateLimitMiddleware(_SlowAPIMiddleware):
    pass

