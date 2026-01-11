import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import run_cleanup
from app.models import LongTermMemory
from app.core.rag_service import rag_service

@pytest.mark.asyncio
async def test_soft_forgetting_logic():
    """Test that records are soft-archived with ultra-summary."""
    db_mock = AsyncMock()
    
    # Mock hard delete result
    mock_hard = MagicMock()
    mock_hard.rowcount = 1
    
    # Mock soft archive targets
    now = datetime.now(timezone.utc)
    old_low_score = LongTermMemory(
        id="m1", 
        summary_text="Deep technical details about something", 
        importance_score=3.0,
        created_at=now - timedelta(days=200),
        is_archived=False
    )
    
    mock_soft_targets = MagicMock()
    mock_soft_targets.scalars.return_value.all.return_value = [old_low_score]
    
    # Mock notes cleanup result
    mock_notes = MagicMock()
    mock_notes.rowcount = 0
    
    db_mock.execute.side_effect = [mock_hard, mock_soft_targets, mock_notes]
    
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.return_value = "Compressed summary"
    
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.cleanup_memory.ai_service", mock_ai):
        
        hard, archived = await run_cleanup()
        
        assert hard == 1
        assert archived == 1
        assert old_low_score.is_archived is True
        assert old_low_score.archived_summary == "Compressed summary"
        db_mock.commit.assert_called_once()

@pytest.mark.asyncio
async def test_restore_archived_memory():
    """Test the restore_memory functionality."""
    db_mock = AsyncMock()
    archived_mem = LongTermMemory(id="m_archived", is_archived=True)
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = archived_mem
    db_mock.execute.return_value = mock_res
    
    success = await rag_service.restore_memory("m_archived", db_mock)
    
    assert success is True
    assert archived_mem.is_archived is False
    db_mock.commit.assert_called_once()
