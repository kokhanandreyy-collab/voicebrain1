import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
import datetime
from app.services.ai_service.cache_handler import CacheHandler
from tasks.reflection import _process_reflection_async

@pytest.mark.asyncio
async def test_cache_handler_scope():
    """Test that CacheHandler scope separates keys and injects metadata."""
    redis = AsyncMock()
    handler = CacheHandler(redis)
    
    # Save with scope
    await handler.save_analysis("txt", {"intent": "x"}, scope="analysis_only")
    
    # Check setex call
    # redis.setex(key, ttl, value)
    args = redis.setex.call_args
    # Key should contain scope
    assert "analysis_only" in args[0][0]
    # Payload should contain _cache_scope
    payload = args[0][2]
    assert '"_cache_scope": "analysis_only"' in payload
    
    # Get with scope
    redis.get.return_value = '{"intent": "x", "_cache_scope": "analysis_only"}'
    res = await handler.get_analysis("txt", scope="analysis_only")
    assert res["_cache_scope"] == "analysis_only"

@pytest.mark.asyncio
async def test_reflection_ignores_cached_notes():
    """Test that reflection skips notes with _cache_scope='analysis_only'."""
    user_id = "u1"
    
    # DB Mock
    db_mock = AsyncMock()
    
    # Mocks
    # 1. User
    m_user_res = MagicMock()
    m_user_res.scalars.return_value.first.return_value = MagicMock(id=user_id, stable_identity="")
    
    # 2. Notes
    # n1: Normal
    n1 = MagicMock(id="n1", transcription_text="n1_text", ai_analysis={}, importance_score=5.0)
    # n2: Cached analysis_only (SHOULD BE IGNORED)
    n2 = MagicMock(id="n2", transcription_text="n2_text", ai_analysis={"_cache_scope": "analysis_only"}, importance_score=5.0)
    # n3: Cached general (should be included)
    n3 = MagicMock(id="n3", transcription_text="n3_text", ai_analysis={"_cache_scope": "general"}, importance_score=5.0)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    for n in [n1, n2, n3]:
        n.created_at = now
        n.action_items = []
    
    m_notes_res = MagicMock()
    m_notes_res.scalars.return_value.all.return_value = [n1, n2, n3]

    m_count = MagicMock()
    m_count.scalar.return_value = 0

    def execute_side_effect(stmt, *args, **kwargs):
        s = str(stmt).lower()
        if "from users" in s: return m_user_res
        if "from notes" in s: return m_notes_res
        if "count" in s: return m_count
        return MagicMock()
    
    db_mock.execute.side_effect = execute_side_effect
    db_mock.__aenter__.return_value = db_mock
    db_mock.__aexit__.return_value = None
    
    # AI Mock
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5}', # Step 1
        '{}', # Step 2
        '[]' # Step 3 (Graph)
    ]
    mock_ai.clean_json_response = MagicMock(side_effect=lambda x: x)
    mock_ai.generate_embedding.return_value = [0.1]*1536

    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor"):
         
        await _process_reflection_async(user_id)
        
        # Verify n2 was excluded from prompt
        # Step 1 call is first call to get_chat_completion
        call_args = mock_ai.get_chat_completion.call_args_list[0]
        prompt = call_args[0][0][1]["content"]
        
        # n1 should be present
        assert "ID: n1" in prompt
        # n3 should be present
        assert "ID: n3" in prompt
        # n2 should NOT be present
        assert "ID: n2" not in prompt
