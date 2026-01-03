import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import cleanup_memory
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_cleanup_notes():
    """Verify that old low-importance notes are deleted."""
    mock_session = AsyncMock()
    # Mock the execute result for the first query (Notes)
    mock_result_notes = MagicMock()
    mock_result_notes.rowcount = 5
    
    # Mock the execute result for the second query (LTM)
    mock_result_ltm = MagicMock()
    mock_result_ltm.rowcount = 2
    
    mock_session.execute.side_effect = [mock_result_notes, mock_result_ltm]
    
    # Patch the session factory used in the task
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
        # The task uses asyncio.run() or loop.run_until_complete() internally
        cleanup_memory()
        
        # Verify calls
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.called
        assert mock_session.rollback.called is False

@pytest.mark.asyncio
async def test_cleanup_longterm():
    """Verify that old low-importance long-term memories are deleted."""
    mock_session = AsyncMock()
    
    # Mock results
    mock_res_notes = MagicMock(rowcount=0)
    mock_res_ltm = MagicMock(rowcount=10)
    
    mock_session.execute.side_effect = [mock_res_notes, mock_res_ltm]
    
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
        cleanup_memory()
        
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.called
