import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete

from tasks.cleanup_memory import run_cleanup
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_cleanup_notes():
    """Test deletion of old low-importance notes."""
    db_mock = AsyncMock()
    mock_res_note = MagicMock()
    mock_res_note.rowcount = 5
    
    mock_res_ltm = MagicMock()
    mock_res_ltm.rowcount = 0
    
    # We expect 2 execute calls (Note cleanup, then LTM cleanup)
    db_mock.execute.side_effect = [mock_res_note, mock_res_ltm]
    
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=db_mock):
        deleted_notes, deleted_ltm = await run_cleanup()
        
        assert deleted_notes == 5
        assert deleted_ltm == 0
        db_mock.commit.assert_called_once()
        
        # Verify Note deletion call
        note_call = db_mock.execute.call_args_list[0]
        stmt = note_call[0][0]
        assert "notes" in str(stmt)
        # Check that it uses importance_score < 4
        assert "importance_score <" in str(stmt)

@pytest.mark.asyncio
async def test_cleanup_longterm():
    """Test deletion of old low-importance long-term memories."""
    db_mock = AsyncMock()
    mock_res_note = MagicMock()
    mock_res_note.rowcount = 0
    
    mock_res_ltm = MagicMock()
    mock_res_ltm.rowcount = 3
    
    # We expect 2 execute calls
    db_mock.execute.side_effect = [mock_res_note, mock_res_ltm]
    
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=db_mock):
        deleted_notes, deleted_ltm = await run_cleanup()
        
        assert deleted_notes == 0
        assert deleted_ltm == 3
        db_mock.commit.assert_called_once()
        
        # Verify LTM deletion call
        ltm_call = db_mock.execute.call_args_list[1]
        stmt = ltm_call[0][0]
        assert "long_term_memories" in str(stmt)
        # Check that it uses importance_score < 5
        assert "importance_score <" in str(stmt)
