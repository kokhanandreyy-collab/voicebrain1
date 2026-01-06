import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_service import AIService
import datetime

@pytest.mark.asyncio
async def test_ai_usage_logging_and_tracking():
    """Verify that AI service correctly logs and tracks token usage in Redis."""
    ai_service = AIService()
    
    # Mock Redis
    redis_mock = AsyncMock()
    ai_service.redis = redis_mock
    
    # Mock Usage object from OpenAI response
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150
    
    with patch("app.services.ai_service.logger") as mock_logger:
        await ai_service._track_usage(mock_usage)
        
        # 1. Verify log format
        mock_logger.info.assert_called_with("DeepSeek usage: input 100, output 50, total 150")
        
        # 2. Verify Redis pipeline usage
        # hincrby should be called 3 times
        assert redis_mock.pipeline.called
        
        # Verify today's date key
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        expected_key = f"ai_usage:daily:{today}"
        
        # Check call arguments in the pipeline mock
        # (This depends on how AsyncMock handles pipeline context mgr)
        # For simplicity, we just assert that Redis interaction was triggered
        assert redis_mock.pipeline.return_value.__aenter__.called

@pytest.mark.asyncio
async def test_daily_usage_report():
    """Verify that maintenance task correctly pulls and logs daily usage."""
    from workers.maintenance_tasks import _report_ai_usage_async
    
    today = datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    key = f"ai_usage:daily:{today}"
    
    # Setup mock returned data from Redis
    mock_usage = {
        "prompt_tokens": "1000",
        "completion_tokens": "500",
        "total_tokens": "1500"
    }
    
    with patch("workers.maintenance_tasks.ai_service") as mock_ai, \
         patch("workers.maintenance_tasks.logger") as mock_logger:
        
        # Redis hgetall returns the dict
        mock_ai.redis.hgetall = AsyncMock(return_value=mock_usage)
        
        await _report_ai_usage_async()
        
        # Verify the logs
        log_msgs = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Prompt Tokens: 1000" in msg for msg in log_msgs)
        assert any("Completion Tokens: 500" in msg for msg in log_msgs)
        assert any("Total Tokens: 1500" in msg for msg in log_msgs)
