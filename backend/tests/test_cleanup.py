import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import cleanup_memory
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_cleanup_notes():
    """Verify that old low-importance notes are deleted via SQLAlchemy delete()."""
    mock_session = AsyncMock()
    mock_res_notes = MagicMock(rowcount=5)
    mock_res_ltm = MagicMock(rowcount=2)
    
    mock_session.execute.side_effect = [mock_res_notes, mock_res_ltm]
    
    # We patch the session factory and asyncio.run to avoid nested loop errors
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
        with patch("asyncio.run", side_effect=lambda coroutine: asyncio.get_event_loop().run_until_complete(coroutine)):
            import asyncio
            cleanup_memory()
            
            assert mock_session.execute.call_count == 2
            assert mock_session.commit.called
            assert mock_session.rollback.called is False

@pytest.mark.asyncio
async def test_cleanup_longterm():
    """Verify deletion logic for LongTermMemory."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = [MagicMock(rowcount=0), MagicMock(rowcount=10)]
    
    with patch("tasks.cleanup_memory.async_session", return_value=mock_session):
         with patch("asyncio.run", side_effect=lambda coroutine: asyncio.get_event_loop().run_until_complete(coroutine)):
            import asyncio
            cleanup_memory()
            
            assert mock_session.execute.call_count == 2
            assert mock_session.commit.called
