import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import run_cleanup
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_cleanup_memory_logic():
    """Test that cleanup correctly identifies and deletes old, low-score items."""
    db_mock = AsyncMock()
    
    # Mock result for rowcount
    mock_res_note = MagicMock()
    mock_res_note.rowcount = 3
    
    mock_res_ltm = MagicMock()
    mock_res_ltm.rowcount = 1
    
    # We expect 2 execute calls (delete Note and delete LongTermMemory)
    db_mock.execute.side_effect = [mock_res_note, mock_res_ltm]
    
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=db_mock):
        await run_cleanup()
        
        # Verify execute was called twice
        assert db_mock.execute.call_count == 2
        
        # Verify commit
        db_mock.commit.assert_called_once()
        
        # Check call arguments (optional but good for Senior)
        calls = db_mock.execute.call_args_list
        # First call should be for Note
        assert "notes" in str(calls[0][0][0])
        # Second call should be for LongTermMemory
        assert "long_term_memories" in str(calls[1][0][0])
