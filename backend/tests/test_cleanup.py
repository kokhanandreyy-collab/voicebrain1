import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import run_cleanup_async
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_cleanup_notes():
    """Verify that old low-importance notes are deleted via SQLAlchemy delete()."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_res_notes = MagicMock()
    mock_res_notes.rowcount = 5
    mock_res_ltm = MagicMock()
    mock_res_ltm.rowcount = 2
    
    mock_session.execute.side_effect = [mock_res_notes, mock_res_ltm]
    
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
        await run_cleanup_async()
        
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.called
        assert mock_session.rollback.called is False

@pytest.mark.asyncio
async def test_cleanup_longterm():
    """Verify deletion logic for LongTermMemory."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.execute.side_effect = [MagicMock(rowcount=0), MagicMock(rowcount=10)]
    
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
         await run_cleanup_async()
         
         assert mock_session.execute.call_count == 2
         assert mock_session.commit.called
