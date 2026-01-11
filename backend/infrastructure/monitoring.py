from prometheus_client import Gauge, Counter
from loguru import logger

# 1. Graph Metrics
memory_graph_nodes = Gauge("memory_graph_nodes", "Total number of notes in the system")
memory_graph_edges = Gauge("memory_graph_edges", "Total number of note relations in the system")

# 2. Reflection/Analysis Cache Metrics
analysis_cache_hits = Counter("analysis_cache_hits_total", "Total number of semantic cache hits", ["type"])
analysis_cache_misses = Counter("analysis_cache_misses_total", "Total number of semantic cache misses", ["type"])

reflection_hit_rate_gauge = Gauge("analysis_cache_hit_rate", "Current analysis cache hit rate (0.0 - 1.0)")
db_query_count = Counter("db_queries_total", "Total number of database queries executed")
reflection_ops_count = Counter("reflection_ops_total", "Total reflection operations triggered")

class MemoryMonitor:
    @staticmethod
    def track_cache_hit(cache_type: str = "semantic"):
        analysis_cache_hits.labels(type=cache_type).inc()
        logger.debug(f"Cache Hit: {cache_type}")

    @staticmethod
    def track_cache_miss(cache_type: str = "semantic"):
        analysis_cache_misses.labels(type=cache_type).inc()
        logger.debug(f"Cache Miss: {cache_type}")

    @staticmethod
    def update_graph_metrics(nodes: int, edges: int):
        memory_graph_nodes.set(nodes)
        memory_graph_edges.set(edges)
        logger.info(f"Graph size: {nodes} nodes, {edges} edges")

    @staticmethod
    def update_hit_rate():
        """Calculates and updates hit rate gauge from counters."""
        hits = sum(c._value.get() for c in analysis_cache_hits._metrics.values())
        misses = sum(c._value.get() for c in analysis_cache_misses._metrics.values())
        total = hits + misses
        if total > 0:
            rate = hits / total
            reflection_hit_rate_gauge.set(rate)
            logger.info(f"Daily reflection cache hit rate: {rate:.2%}")
        else:
            logger.info("Daily reflection cache hit rate: N/A (no requests)")

    @staticmethod
    def track_db_query():
        db_query_count.inc()

    @staticmethod
    def track_reflection_start():
        reflection_ops_count.inc()

monitor = MemoryMonitor()
