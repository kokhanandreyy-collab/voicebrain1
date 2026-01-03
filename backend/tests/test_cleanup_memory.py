import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from workers.maintenance_tasks import _cleanup_memory_async
from app.models import Note, LongTermMemory

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_cleanup_memory_logic(mock_db_session):
    """Test cleanup of Notes and LongTermMemory based on score and age."""
    
    # 1. Setup Mock Data
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=200) # Older than 180
    recent_date = now - timedelta(days=10)
    
    # Notes
    note_old_low = Note(id="n1", importance_score=3.0, created_at=old_date, storage_key="s3_key_1")
    note_old_high = Note(id="n2", importance_score=8.0, created_at=old_date)
    note_recent_low = Note(id="n3", importance_score=3.0, created_at=recent_date)
    
    # LTM
    ltm_old_low = LongTermMemory(id="m1", importance_score=4.0, created_at=old_date)
    ltm_old_high = LongTermMemory(id="m2", importance_score=9.0, created_at=old_date)
    ltm_recent_low = LongTermMemory(id="m3", importance_score=4.0, created_at=recent_date) # Needs 180 days, so safe
    
    # 2. Mock DB Execution for Notes
    # The function calls: select(Note)... then select(LongTermMemory)...
    
    mock_notes_res = MagicMock()
    mock_notes_res.scalars().all.return_value = [note_old_low] # Expect n1 to be selected
    
    mock_ltm_res = MagicMock()
    mock_ltm_res.scalars().all.return_value = [ltm_old_low] # Expect m1 to be selected
    
    mock_db_session.execute.side_effect = [mock_notes_res, mock_ltm_res]
    
    # 3. Patch dependencies
    with patch("workers.maintenance_tasks.AsyncSessionLocal") as mock_session_cls, \
         patch("workers.maintenance_tasks.storage_client") as mock_storage:
         
         mock_session_cls.return_value = mock_db_session
         mock_session_cls.return_value.__aenter__.return_value = mock_db_session # Support async context if used, but here it's instantiation
         # The function uses `db = AsyncSessionLocal()`, not `async with ..`? Let's check source code.
         # Source code: db = AsyncSessionLocal() ... finally: await db.close()
         # So return_value is enough.
         
         await _cleanup_memory_async()
         
         # 4. Verify Deletions
         # Notes: Only n1 should be deleted (score 3 < 4 and old)
         # LTM: Only m1 should be deleted (score 4 < 5 and old)
         
         assert mock_db_session.delete.call_count == 2
         
         deleted_items = [call.args[0] for call in mock_db_session.delete.call_args_list]
         assert note_old_low in deleted_items
         assert ltm_old_low in deleted_items
         
         # check S3 deletion
         mock_storage.delete_file.assert_called_with("s3_key_1")

