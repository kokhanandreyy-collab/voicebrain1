
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from tasks.reflection import reflection_batch, trigger_batched_reflection, _process_batch_wrapper, _trigger_batched_async

@pytest.mark.asyncio
async def test_process_batch_wrapper():
    """Test that batch wrapper calls process_reflection for each user."""
    user_ids = ["u1", "u2", "u3"]
    
    with patch("tasks.reflection._process_reflection_async", new_callable=AsyncMock) as mock_process:
        await _process_batch_wrapper(user_ids)
        assert mock_process.call_count == 3
        mock_process.assert_any_call("u1")
        mock_process.assert_any_call("u2")
        mock_process.assert_any_call("u3")

@pytest.mark.asyncio
async def test_trigger_batched_async():
    """Test that trigger chunks users and calls batch task."""
    
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_db.__aenter__.return_value = mock_session
    
    # Create 120 mock users
    users = [MagicMock(id=f"user_{i}") for i in range(120)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = users
    mock_session.execute.return_value = mock_result
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=mock_db), \
         patch("tasks.reflection.reflection_batch.delay") as mock_delay:
        
        await _trigger_batched_async()
        
        # Should have called delay for chunks of 50
        # 120 users -> 50, 50, 20 -> 3 calls
        assert mock_delay.call_count == 3
        
        args_list = mock_delay.call_args_list
        # Check first chunk size
        assert len(args_list[0][0][0]) == 50
        assert len(args_list[1][0][0]) == 50
        assert len(args_list[2][0][0]) == 20
