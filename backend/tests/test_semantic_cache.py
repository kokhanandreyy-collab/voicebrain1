import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json
from app.models import Note, User, CachedAnalysis, NoteStatus

@pytest.mark.asyncio
async def test_semantic_cache_hit():
    """Test that a cache hit bypasses AI call and returns cached result."""
    from app.core.analyze_core import AnalyzeCore

    # Mock dependencies
    mock_db = AsyncMock()
    mock_memory_service = AsyncMock()
    mock_memory_service.get_history.return_value = []
    
    # Mock AI Service
    with patch("app.core.analyze_core.ai_service") as mock_ai:
        mock_ai.generate_embedding = AsyncMock(return_value=[0.1]*1536)
        # analyze_text should NOT be called on hit
        mock_ai.analyze_text = AsyncMock(return_value={"title": "Should Not Run"})

        # Mock DB Cache Hit
        mock_cached_entry = MagicMock()
        mock_cached_entry.result = {
            "title": "Cached Title",
            "summary": "Cached Summary", 
            "intent": "note"
        }
        
        # scalars().first() -> cached_entry
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_cached_entry
        mock_db.execute.return_value = mock_result

        # Setup Input
        note = Note(
            id="test-note-1", 
            user_id="user-1", 
            transcription_text="This is a duplicate test note."
        )
        user = User(id="user-1")

        # Run
        core = AnalyzeCore()
        analysis = await core.analyze_step(note, user, mock_db, mock_memory_service)

        # Assertions
        assert analysis["title"] == "Cached Title"
        mock_ai.analyze_text.assert_not_called()
        # Verify Log (implicitly via logic flow or capturing logs, but unit test focuses on result)
        
        # Verify NO new save to cache (db.add should not be called for cache, only for embedding/note updates if any)
        # Actually in code, db.add is called for NoteEmbedding later. But for Cache it shouldn't be added again.
        # We can check specific db.add calls if we wanted precision.

@pytest.mark.asyncio
async def test_semantic_cache_miss():
    """Test that a cache miss triggers AI call and saves to cache."""
    from app.core.analyze_core import AnalyzeCore

    # Mock dependencies
    mock_db = AsyncMock()
    mock_memory_service = AsyncMock()
    mock_memory_service.get_history.return_value = []
    
    with patch("app.core.analyze_core.ai_service") as mock_ai:
        mock_ai.generate_embedding = AsyncMock(return_value=[0.2]*1536)
        mock_ai.analyze_text = AsyncMock(return_value={
            "title": "Fresh AI Title",
            "summary": "Fresh Summary",
            "intent": "task"
        })

        # Mock DB Cache Miss
        # scalars().first() -> None
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        
        # We need extensive mocking for chained calls or simply:
        # First execute is checking cache -> returns None
        # Subsequent executes (e.g. for user update) -> mock them too or ignore
        mock_db.execute.return_value = mock_result

        # Setup Input
        note = Note(
            id="test-note-2",
            user_id="user-1",
            transcription_text="Unique new content."
        )
        user = User(id="user-1")

        # Run
        core = AnalyzeCore()
        analysis = await core.analyze_step(note, user, mock_db, mock_memory_service)

        # Assertions
        assert analysis["title"] == "Fresh AI Title"
        mock_ai.analyze_text.assert_called_once()
        
        # Verify Cache Save
        # db.add should be called with a CachedAnalysis instance
        args, _ = mock_db.add.call_args_list[0] # First add might be Cache or Embedding
        # The code adds Cache then Embedding. Or Embedding then Cache?
        # Let's inspect call_args_list to find CachedAnalysis
        saved_cache = None
        for call in mock_db.add.call_args_list:
            arg = call[0][0]
            if isinstance(arg, CachedAnalysis):
                saved_cache = arg
                break
        
        assert saved_cache is not None
        assert saved_cache.user_id == "user-1"
        assert saved_cache.result["title"] == "Fresh AI Title"
