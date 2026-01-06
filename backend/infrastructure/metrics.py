from prometheus_client import Counter, Gauge
import redis
from infrastructure.config import settings

# Redis connection for global stats
r = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Semantic Cache Metrics
CACHE_HITS = Counter("cache_hits", "Total cache hits", ["type"])
CACHE_MISSES = Counter("cache_misses", "Total cache misses", ["type"])

# Graph Metrics (Requirement 3)
MEMORY_GRAPH_NODES = Gauge("memory_graph_size_nodes", "Total number of nodes (notes) in memory graph")
MEMORY_GRAPH_EDGES = Gauge("memory_graph_size_edges", "Total number of edges (relations) in memory graph")
REFLECTION_HIT_RATE_GAUGE = Gauge("reflection_hit_rate_percent", "Current hit rate % for reflection cache")

def track_cache_hit(cache_type: str):
    CACHE_HITS.labels(type=cache_type).inc()
    try:
        r.incr(f"stats:cache_hits:{cache_type}")
        r.incr("stats:cache_hits")
    except Exception:
        pass

def track_cache_miss(cache_type: str):
    CACHE_MISSES.labels(type=cache_type).inc()
    try:
        r.incr(f"stats:cache_misses:{cache_type}")
        r.incr("stats:cache_misses")
    except Exception:
        pass

def get_cache_hit_rate() -> float:
    """Calculates global cache hit rate %."""
    try:
        hits = int(r.get("stats:cache_hits") or 0)
        misses = int(r.get("stats:cache_misses") or 0)
        total = hits + misses
        return round((hits / total) * 100, 2) if total > 0 else 0.0
    except Exception:
        return 0.0

def get_reflection_hit_rate() -> float:
    """Calculates reflection-specific cache hit rate % (Requirement 2/3)."""
    try:
        hits = int(r.get("stats:cache_hits:reflection") or 0)
        misses = int(r.get("stats:cache_misses:reflection") or 0)
        total = hits + misses
        if total == 0: return 0.0
        val = round((hits / total) * 100, 2)
        REFLECTION_HIT_RATE_GAUGE.set(val)
        return val
    except Exception:
        return 0.0
