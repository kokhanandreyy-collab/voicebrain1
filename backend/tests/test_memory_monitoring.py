import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.reflection import _process_reflection_async
from infrastructure.monitoring import monitor

@pytest.mark.asyncio
async def test_memory_monitoring_update():
    """Test that graph metrics and hit rate are updated during reflection."""
    user_id = "u1"
    db_mock = AsyncMock()
    
    # Mock counts
    # select(func.count(Note.id))
    # select(func.count(NoteRelation.id))
    # select(User)
    # select(Note)
    count_notes = MagicMock()
    count_notes.scalar.return_value = 100
    
    count_rels = MagicMock()
    count_rels.scalar.return_value = 50
    
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = None # Stop early after metrics
    
    db_mock.execute.side_effect = [count_notes, count_rels, user_res]
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("infrastructure.monitoring.memory_graph_nodes") as mock_nodes, \
         patch("infrastructure.monitoring.memory_graph_edges") as mock_edges:
        
        await _process_reflection_async(user_id)
        
        # Verify Prometheus metrics were updated
        mock_nodes.set.assert_called_with(100)
        mock_edges.set.assert_called_with(50)

def test_hit_rate_calculation():
    """Test the hit rate math in MemoryMonitor."""
    with patch("infrastructure.monitoring.analysis_cache_hits") as mock_hits, \
         patch("infrastructure.monitoring.analysis_cache_misses") as mock_misses, \
         patch("infrastructure.monitoring.reflection_hit_rate_gauge") as mock_gauge:
        
        # Setup mock metrics values
        h1 = MagicMock(); h1._value.get.return_value = 80
        m1 = MagicMock(); m1._value.get.return_value = 20
        
        mock_hits._metrics = {(): h1}
        mock_misses._metrics = {(): m1}
        
        monitor.update_hit_rate()
        
        # 80 / (80+20) = 0.8
        mock_gauge.set.assert_called_with(0.8)
