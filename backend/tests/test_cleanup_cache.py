import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from app.models import CachedAnalysis

@pytest.mark.asyncio
async def test_cleanup_cache_deletes_expired():
    """Test that cleanup task deletes only expired entries."""
    from tasks.cleanup_cache import _cleanup_cache_async
    
    mock_db = AsyncMock()
    
    # Mock result of execute for delete statement
    mock_execute_result = MagicMock()
    mock_execute_result.rowcount = 5
    mock_db.execute.return_value = mock_execute_result
    
    with patch("tasks.cleanup_cache.AsyncSessionLocal", return_value=mock_db):
        deleted_count = await _cleanup_cache_async()
        
        # Verify Execute was called
        assert mock_db.execute.called
        # Verify result count
        assert deleted_count == 5
        # Verify Commit
        mock_db.commit.assert_called_once()
        
@pytest.mark.asyncio
async def test_cleanup_cache_no_expired():
    """Test cleanup when no expired entries exist."""
    from tasks.cleanup_cache import _cleanup_cache_async
    
    mock_db = AsyncMock()
    
    mock_execute_result = MagicMock()
    mock_execute_result.rowcount = 0
    mock_db.execute.return_value = mock_execute_result
    
    with patch("tasks.cleanup_cache.AsyncSessionLocal", return_value=mock_db):
        deleted_count = await _cleanup_cache_async()
        
        assert deleted_count == 0
        mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup_cache_handles_error():
    """Test cleanup resilience on DB error."""
    from tasks.cleanup_cache import _cleanup_cache_async
    
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Error")
    
    with patch("tasks.cleanup_cache.AsyncSessionLocal", return_value=mock_db):
        deleted_count = await _cleanup_cache_async()
        
        assert deleted_count == 0
        mock_db.rollback.assert_called_once()
