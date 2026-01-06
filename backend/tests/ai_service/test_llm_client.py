import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_service.llm_client import LLMClient

@pytest.mark.asyncio
async def test_track_usage_logging():
    redis_mock = AsyncMock()
    client = LLMClient(redis_mock)
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5
    mock_usage.total_tokens = 15
    
    await client._track_usage(mock_usage)
    
    # Verify Redis interaction
    assert redis_mock.pipeline.called
    # Check if pipeline increment was called for tokens
    pipe_mock = redis_mock.pipeline.return_value.__aenter__.return_value
    assert pipe_mock.hincrby.called

@pytest.mark.asyncio
async def test_get_completion_retry_mock():
    # Patch settings to skip real calls
    with patch("app.services.ai_service.llm_client.AsyncOpenAI") as mock_openai:
        client = LLMClient(None)
        client.deepseek_client = AsyncMock()
        client.deepseek_key = "test-key"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="{\"res\":1}"))]
        mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        client.deepseek_client.chat.completions.create.return_value = mock_response
        
        res = await client.get_completion(messages=[], model="deepseek-chat")
        assert res.choices[0].message.content == "{\"res\":1}"
