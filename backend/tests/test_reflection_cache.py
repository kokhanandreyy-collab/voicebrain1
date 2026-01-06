import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import json
from app.models import Note, User, CachedAnalysis, LongTermMemory

@pytest.mark.asyncio
async def test_reflection_cache_hit():
    """Test that a reflection cache hit reuses data and skips AI call."""
    from workers.reflection_tasks import _process_reflection_async
    
    # Setup Mocks
    mock_db = AsyncMock()
    
    # Mock last 50 notes
    notes = [Note(id=f"n{i}", user_id="u1", transcription_text=f"Note {i}", created_at=datetime.now()) for i in range(5)]
    mock_result_notes = MagicMock()
    mock_result_notes.scalars.return_value.all.return_value = notes
    
    # Mock Cache Hit
    mock_cached_entry = MagicMock()
    mock_cached_entry.result = {
        "summary": "Cached Reflection Summary",
        "identity_summary": "Cached Identity",
        "importance_score": 9.0
    }
    mock_result_cache = MagicMock()
    mock_result_cache.scalars.return_value.first.return_value = mock_cached_entry
    
    # Mock Database sequence
    # 1. Fetch notes
    # 2. Fetch cache
    # 3. Fetch user for identity update
    # 4. Success commit
    mock_db.execute.side_effect = [mock_result_notes, mock_result_cache, AsyncMock()]

    with patch("workers.reflection_tasks.ai_service") as mock_ai:
        mock_ai.generate_embedding = AsyncMock(return_value=[0.1]*1536)
        mock_ai.get_chat_completion = AsyncMock() # Should NOT be called
        
        # We need mock for AsyncSessionLocal context manager
        with patch("workers.reflection_tasks.AsyncSessionLocal", return_value=mock_db):
            await _process_reflection_async("u1")
            
            # Assertions
            mock_ai.get_chat_completion.assert_not_called()
            # Verify LongTermMemory was added (for the hit result)
            hit_added = False
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, LongTermMemory) and obj.summary_text == "Cached Reflection Summary":
                    hit_added = True
            assert hit_added is True

@pytest.mark.asyncio
async def test_reflection_cache_miss():
    """Test that a reflection cache miss calls AI and saves to cache."""
    from workers.reflection_tasks import _process_reflection_async
    
    mock_db = AsyncMock()
    
    # Mock last 50 notes
    notes = [Note(id=f"n{i}", user_id="u1", transcription_text=f"Note {i}", created_at=datetime.now()) for i in range(5)]
    mock_result_notes = MagicMock()
    mock_result_notes.scalars.return_value.all.return_value = notes
    
    # Mock Cache Miss
    mock_result_cache = MagicMock()
    mock_result_cache.scalars.return_value.first.return_value = None
    
    mock_db.execute.side_effect = [mock_result_notes, mock_result_cache, AsyncMock(), AsyncMock()]

    with patch("workers.reflection_tasks.ai_service") as mock_ai:
        mock_ai.generate_embedding = AsyncMock(return_value=[0.2]*1536)
        mock_ai.get_chat_completion = AsyncMock(return_value=json.dumps({
            "summary": "Fresh AI Reflection",
            "identity_summary": "Fresh Identity",
            "importance_score": 7.0
        }))
        mock_ai.clean_json_response = lambda x: x
        mock_ai.get_embedding = AsyncMock(return_value=[0.3]*1536)
        
        with patch("workers.reflection_tasks.AsyncSessionLocal", return_value=mock_db):
            await _process_reflection_async("u1")
            
            # Assertions
            mock_ai.get_chat_completion.assert_called_once()
            
            # Verify Cache Save
            saved_cache = None
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, CachedAnalysis):
                    saved_cache = obj
            
            assert saved_cache is not None
            assert saved_cache.result["summary"] == "Fresh AI Reflection"
            # Verify TTL is ~7 days
            expected_exp = datetime.now(timezone.utc) + timedelta(days=7)
            assert (saved_cache.expires_at - expected_exp).total_seconds() < 60
