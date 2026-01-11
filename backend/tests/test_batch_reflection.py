import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _trigger_batched_async, _process_batch_wrapper
from app.models import User
import datetime

@pytest.mark.asyncio
async def test_trigger_batches():
    """
    Test that users are chunked into 50 and tasks are dispatched.
    """
    # 1. Setup Mock DB with 120 users
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    users = [User(id=f"u{i}", is_active=True) for i in range(120)]
    
    mock_user_res = MagicMock()
    mock_user_res.scalars.return_value.all.return_value = users
    mock_db.execute.return_value = mock_user_res
    
    # 2. Patch trigger task and Celery delay
    with patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls, \
         patch("workers.reflection_tasks.batch_reflection.delay") as mock_delay:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         
         await _trigger_batched_async()
         
         # 3. Assertions
         # 120 users / 50 = 3 chunks (50, 50, 20)
         assert mock_delay.call_count == 3
         
         # Verify chunk sizes
         call_args = mock_delay.call_args_list
         chunk1 = call_args[0][0][0]
         chunk2 = call_args[1][0][0]
         chunk3 = call_args[2][0][0]
         
         assert len(chunk1) == 50
         assert len(chunk2) == 50
         assert len(chunk3) == 20

@pytest.mark.asyncio
async def test_batch_execution():
    """
    Test that batch wrapper calls process logic for each user.
    """
    user_ids = ["u1", "u2", "u3"]
    
    with patch("workers.reflection_tasks._process_reflection_async", new_callable=AsyncMock) as mock_process:
        await _process_batch_wrapper(user_ids)
        
        assert mock_process.call_count == 3
        # Verify calls
        mock_process.assert_any_call("u1")
        mock_process.assert_any_call("u2")
        mock_process.assert_any_call("u3")
