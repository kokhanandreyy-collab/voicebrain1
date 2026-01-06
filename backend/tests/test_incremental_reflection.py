import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from workers.reflection_tasks import reflection_incremental

@pytest.mark.asyncio
async def test_reflection_incremental_lock():
    """Test that incremental reflection honors the Redis lock."""
    user_id = "test_user"
    
    with patch("redis.from_url") as mock_redis_factory:
        mock_redis = MagicMock()
        mock_redis_factory.return_value = mock_redis
        
        # 1. Mock lock exists
        mock_redis.get.return_value = "1"
        
        with patch("workers.reflection_tasks._process_reflection_async") as mock_process:
            reflection_incremental(user_id)
            
            # Should NOT call process
            mock_process.assert_not_called()
            # Should NOT set lock again
            mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_reflection_incremental_trigger():
    """Test that incremental reflection triggers correctly if no lock."""
    user_id = "test_user"
    
    with patch("redis.from_url") as mock_redis_factory:
        mock_redis = MagicMock()
        mock_redis_factory.return_value = mock_redis
        
        # 1. Mock lock NOT exists
        mock_redis.get.return_value = None
        
        with patch("workers.reflection_tasks._process_reflection_async") as mock_process:
            reflection_incremental(user_id)
            
            # Should set lock for 5 mins (300s)
            mock_redis.setex.assert_called_with(f"reflection_lock:{user_id}", 300, "1")
            
            # Should call process with limit=11
            mock_process.assert_called_once()
            args, kwargs = mock_process.call_args
            assert args[0] == user_id
            assert kwargs["limit"] == 11
