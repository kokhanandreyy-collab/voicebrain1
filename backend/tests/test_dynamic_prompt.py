import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.analyze_tasks import _process_analyze_async
from app.models import Note, User, CachedAnalysis
import json
import datetime

@pytest.mark.asyncio
async def test_dynamic_prompt_injections():
    """Verify that identity, preferences, and long-term memory are injected only when present."""
    note_id = "note_1"
    
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.id = note_id
    note.user_id = "user_1"
    note.transcription_text = "Hello world"
    note.ai_analysis = {}
    
    user = MagicMock(spec=User)
    user.id = "user_1"
    user.identity_summary = "I am a developer"
    user.adaptive_preferences = {"theme": "dark"}
    user.bio = "Bio"
    user.target_language = "Original"
    user.emotion_history = []
    
    db_mock.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=note)))), # Get note
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=user)))), # Get user
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))), # Cache miss
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),      # RAG history
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),      # RAG vector
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),      # RAG long-term
    ]

    with patch("workers.analyze_tasks.ai_service") as mock_ai, \
         patch("workers.analyze_tasks.AsyncSessionLocal", return_value=db_mock), \
         patch("workers.analyze_tasks.short_term_memory"), \
         patch("workers.analyze_tasks.track_cache_miss"), \
         patch("workers.analyze_tasks.rag_service") as mock_rag:
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {"title": "Test", "summary": "Test"}
        mock_rag.get_long_term_memory.return_value = "Memory item 1"
        
        await _process_analyze_async(note_id)
        
        # Check if analyze_text was called with injected context
        args, kwargs = mock_ai.analyze_text.call_args
        user_context = kwargs.get("user_context", "")
        
        assert "User identity: I am a developer" in user_context
        assert "Adaptive preferences: {\"theme\": \"dark\"}" in user_context
        assert "Long-term knowledge: Memory item 1" in user_context

@pytest.mark.asyncio
async def test_cache_hit_skips_ai():
    """Verify that a semantic cache hit bypasses the AI call."""
    note_id = "note_1"
    db_mock = AsyncMock()
    
    cached_result = {"title": "Cached", "summary": "Cached"}
    cache_entry = MagicMock(spec=CachedAnalysis)
    cache_entry.result = cached_result
    
    note = MagicMock(spec=Note)
    note.user_id = "user_1"
    
    db_mock.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=note)))), # Get note
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=MagicMock())))), # Get user
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=cache_entry)))), # Cache hit!
    ]

    with patch("workers.analyze_tasks.ai_service") as mock_ai, \
         patch("workers.analyze_tasks.AsyncSessionLocal", return_value=db_mock), \
         patch("workers.analyze_tasks.track_cache_hit"):
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        
        await _process_analyze_async(note_id)
        
        # AI analyze_text should NOT be called
        mock_ai.analyze_text.assert_not_called()
        # Note should be updated from cache
        assert note.title == "Cached"
