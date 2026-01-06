import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.metrics import track_cache_hit, track_cache_miss, get_reflection_hit_rate
import redis

@pytest.mark.asyncio
async def test_reflection_monitoring_metrics():
    """Test that reflection hit/miss tracking works and produces a valid hit rate."""
    
    # Mock redis
    mock_redis = MagicMock()
    # stats:cache_hits:reflection = 8, stats:cache_misses:reflection = 2 -> 80%
    mock_redis.get.side_effect = lambda k: {
        "stats:cache_hits:reflection": "8",
        "stats:cache_misses:reflection": "2"
    }.get(k)
    
    with patch("infrastructure.metrics.r", mock_redis):
        # 1. Track a hit
        track_cache_hit("reflection")
        mock_redis.incr.assert_any_call("stats:cache_hits:reflection")
        
        # 2. Track a miss
        track_cache_miss("reflection")
        mock_redis.incr.assert_any_call("stats:cache_misses:reflection")
        
        # 3. Calculate hit rate
        rate = get_reflection_hit_rate()
        assert rate == 80.0

@pytest.mark.asyncio
async def test_graph_size_updates():
    """Test that graph size Gauges are updated correctly in the reflection task."""
    from workers.reflection_tasks import _process_reflection_async
    
    db_mock = AsyncMock()
    # Mocking counts: 100 nodes, 250 edges
    db_mock.execute.side_effect = [
        MagicMock(scalar=lambda: 100), # nodes
        MagicMock(scalar=lambda: 250), # edges
        # ... rest of the notes fetching etc
    ]
    
    with patch("workers.reflection_tasks.MEMORY_GRAPH_NODES") as mock_nodes_gauge, \
         patch("workers.reflection_tasks.MEMORY_GRAPH_EDGES") as mock_edges_gauge, \
         patch("workers.reflection_tasks.AsyncSessionLocal", return_value=db_mock), \
         patch("workers.reflection_tasks.select", lambda x: x): # simplified select for mock
        
        # We only need to trigger the start of the function to see the graph stats check
        try:
            await _process_reflection_async("user123")
        except Exception:
            pass # We expect it to fail later due to heavy mocking, but gauges should be set
            
        mock_nodes_gauge.set.assert_called_with(100)
        mock_edges_gauge.set.assert_called_with(250)
