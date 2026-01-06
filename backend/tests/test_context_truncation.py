import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.analyze_tasks import _process_analyze_async
from app.models import Note, User
import json

@pytest.mark.asyncio
async def test_context_truncation_logic():
    """Verify that context is truncated when it exceeds 800 tokens."""
    note_id = "note_1"
    db_mock = AsyncMock()
    
    # Large context setup
    large_identity = "I am a developer. " * 200 # ~3000 chars
    large_prefs = {"key": "value " * 200} # ~2000 chars
    large_long_term = "Memory details... " * 300 # ~5000 chars
    
    note = MagicMock(spec=Note)
    note.id = note_id
    note.user_id = "user_1"
    note.transcription_text = "Important note."
    note.ai_analysis = {}
    
    user = MagicMock(spec=User)
    user.id = "user_1"
    user.identity_summary = large_identity
    user.adaptive_preferences = large_prefs
    user.target_language = "Original"
    user.email = "test@example.com"
    
    # Mock DB results
    db_mock.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=note)))), # Get note
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=user)))), # Get user
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))), # Cache miss
    ]

    with patch("workers.analyze_tasks.ai_service") as mock_ai, \
         patch("workers.analyze_tasks.AsyncSessionLocal", return_value=db_mock), \
         patch("workers.analyze_tasks.rag_service") as mock_rag, \
         patch("workers.analyze_tasks.track_cache_miss"), \
         patch("workers.analyze_tasks.logger") as mock_logger:
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        # Simulate long-term memory return
        mock_rag.get_long_term_memory.return_value = large_long_term
        # Simulate short-term/recent
        mock_rag.build_hierarchical_context.return_value = "Recent items..."
        
        mock_ai.analyze_text.return_value = {"title": "Truncated", "summary": "Test"}
        
        await _process_analyze_async(note_id)
        
        # Verify logger.warning was called for truncation
        found_log = False
        for call in mock_logger.warning.call_args_list:
            if "Context truncated" in call.args[0]:
                found_log = True
                break
        assert found_log
        
        # Verify that ai_service.analyze_text was called with a sliced context
        args, kwargs = mock_ai.analyze_text.call_args
        user_context = kwargs.get("user_context", "")
        
        # Total tokens should be around 800 * 4 = 3200 chars. 
        # If successfully truncated, the combined length should be capped.
        assert len(user_context) <= 4000 # Buffer for headers
