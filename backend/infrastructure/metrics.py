from prometheus_client import Counter

# Semantic Cache Metrics
CACHE_HITS = Counter(
    "semantic_cache_hits_total", 
    "Total number of semantic cache hits",
    ["type"] # e.g., "note_analysis", "reflection"
)

CACHE_MISSES = Counter(
    "semantic_cache_misses_total", 
    "Total number of semantic cache misses",
    ["type"]
)

def track_cache_hit(cache_type: str):
    CACHE_HITS.labels(type=cache_type).inc()

def track_cache_miss(cache_type: str):
    CACHE_MISSES.labels(type=cache_type).inc()
