import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.ai_service.cache_handler import CacheHandler
import json

@pytest.mark.asyncio
async def test_cache_analysis_flow():
    redis_mock = AsyncMock()
    handler = CacheHandler(redis_mock)
    
    text = "Hello world"
    result = {"title": "Test"}
    
    # Save
    await handler.save_analysis(text, result)
    assert redis_mock.setex.called
    
    # Get (Hit)
    redis_mock.get.return_value = json.dumps(result)
    hit = await handler.get_analysis(text)
    assert hit == result
    
    # Get (Miss)
    redis_mock.get.return_value = None
    miss = await handler.get_analysis("Unknown")
    assert miss is None
