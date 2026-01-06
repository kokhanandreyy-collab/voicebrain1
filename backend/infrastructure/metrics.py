from prometheus_client import Counter
import redis
from infrastructure.config import settings

# Redis connection for global stats
r = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Semantic Cache Metrics
CACHE_HITS = Counter(
    "cache_hits", 
    "Total number of semantic cache hits",
    ["type"] # e.g., "note_analysis", "reflection"
)

CACHE_MISSES = Counter(
    "cache_misses", 
    "Total number of semantic cache misses",
    ["type"]
)

def track_cache_hit(cache_type: str):
    CACHE_HITS.labels(type=cache_type).inc()
    try:
        r.incr("stats:cache_hits")
    except Exception:
        pass

def track_cache_miss(cache_type: str):
    CACHE_MISSES.labels(type=cache_type).inc()
    try:
        r.incr("stats:cache_misses")
    except Exception:
        pass

def get_cache_hit_rate() -> float:
    """Calculates global cache hit rate %."""
    try:
        hits = int(r.get("stats:cache_hits") or 0)
        misses = int(r.get("stats:cache_misses") or 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    except Exception:
        return 0.0
