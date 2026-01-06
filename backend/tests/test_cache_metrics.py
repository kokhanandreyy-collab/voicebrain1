import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import Note, User, CachedAnalysis
from infrastructure.metrics import CACHE_HITS, CACHE_MISSES

@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus counters before each test."""
    CACHE_HITS.labels(type="note_analysis")._value.set(0)
    CACHE_MISSES.labels(type="note_analysis")._value.set(0)
    CACHE_HITS.labels(type="reflection")._value.set(0)
    CACHE_MISSES.labels(type="reflection")._value.set(0)

@pytest.mark.asyncio
async def test_analyze_cache_metrics_hit():
    """Test that cache hits increment appropriate metrics."""
    from app.core.analyze_core import AnalyzeCore
    
    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    mock_memory.get_history.return_value = []
    
    # Mock Hit
    mock_cached = MagicMock()
    mock_cached.result = {"title": "Cached"}
    mock_db.execute.return_value.scalars().first.return_value = mock_cached
    
    with patch("app.core.analyze_core.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        core = AnalyzeCore()
        await core.analyze_step(Note(id="n1", user_id="u1"), User(id="u1"), mock_db, mock_memory)
        
        # Verify metric
        assert CACHE_HITS.labels(type="note_analysis")._value.get() == 1
        assert CACHE_MISSES.labels(type="note_analysis")._value.get() == 0

@pytest.mark.asyncio
async def test_analyze_cache_metrics_miss():
    """Test that cache misses increment appropriate metrics."""
    from app.core.analyze_core import AnalyzeCore
    
    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    mock_memory.get_history.return_value = []
    
    # Mock Miss
    mock_db.execute.return_value.scalars().first.return_value = None
    
    with patch("app.core.analyze_core.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {"title": "Fresh"}
        core = AnalyzeCore()
        await core.analyze_step(Note(id="n1", user_id="u1"), User(id="u1"), mock_db, mock_memory)
        
        # Verify metric
        assert CACHE_HITS.labels(type="note_analysis")._value.get() == 0
        assert CACHE_MISSES.labels(type="note_analysis")._value.get() == 1

@pytest.mark.asyncio
async def test_reflection_cache_metrics_hit():
    """Test that reflection cache hits increment appropriate metrics."""
    from workers.reflection_tasks import _process_reflection_async
    
    mock_db = AsyncMock()
    
    # Mock notes exist, then cache hit
    mock_notes = MagicMock()
    mock_notes.scalars().all.return_value = [Note(id="n1", transcription_text="t")]
    mock_cached = MagicMock()
    mock_cached.result = {"summary": "s"}
    mock_db.execute.side_effect = [mock_notes, MagicMock()]
    mock_db.execute.return_value.scalars().first.side_effect = [mock_cached, MagicMock()]
    
    with patch("workers.reflection_tasks.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        # Need to patch AsyncSessionLocal to return mock_db
        with patch("workers.reflection_tasks.AsyncSessionLocal", return_value=mock_db):
            await _process_reflection_async("u1")
            
            assert CACHE_HITS.labels(type="reflection")._value.get() == 1
            assert CACHE_MISSES.labels(type="reflection")._value.get() == 0
