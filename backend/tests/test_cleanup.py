import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from app.models import Note, LongTermMemory
from tasks.cleanup_memory import _cleanup_memory_async

@pytest.mark.asyncio
async def test_cleanup_notes():
    """Test cleanup of old low-score notes."""
    mock_db = AsyncMock()
    cutoff_notes = datetime.now(timezone.utc) - timedelta(days=91)
    
    # n1: score 3, old -> DELETE
    # n2: score 5, old -> KEEP (score)
    # n3: score 3, recent -> KEEP (date)
    n1 = Note(id="n1", importance_score=3.0, created_at=cutoff_notes)
    
    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [n1]
    
    # We expect 2 execute calls: 1 for notes, 1 for LTM
    # First call returns notes
    mock_db.execute.side_effect = [
        mock_res, # Notes Query
        MagicMock(scalars=lambda: MagicMock(all=lambda: [])) # LTM Query (empty for this test)
    ]
    mock_db.delete = MagicMock()
    mock_db.__aenter__.return_value = mock_db

    mock_storage = MagicMock()
    mock_storage.delete_file = AsyncMock() # Fix await error

    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=mock_db), \
         patch("tasks.cleanup_memory.storage_client", mock_storage):
         
         await _cleanup_memory_async()
         
         deleted_calls = [call.args[0] for call in mock_db.delete.call_args_list]
         print(f"DEBUG: Deleted: {deleted_calls}")
         assert n1 in deleted_calls
         assert mock_db.commit.called

@pytest.mark.asyncio
async def test_cleanup_longterm():
    """Test cleanup of old low-score LongTermMemory."""
    mock_db = AsyncMock()
    cutoff_ltm = datetime.now(timezone.utc) - timedelta(days=181)
    
    # m1: score 4, old -> DELETE
    m1 = LongTermMemory(id="m1", importance_score=4.0, created_at=cutoff_ltm)
    
    mock_ltm_res = MagicMock()
    mock_ltm_res.scalars().all.return_value = [m1]
    
    mock_db.execute.side_effect = [
        MagicMock(scalars=lambda: MagicMock(all=lambda: [])), # Notes Query (empty)
        mock_ltm_res # LTM Query
    ]
    mock_db.delete = MagicMock()
    mock_db.__aenter__.return_value = mock_db

    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=mock_db):
         await _cleanup_memory_async()
         
         deleted_calls = [call.args[0] for call in mock_db.delete.call_args_list]
         assert m1 in deleted_calls
