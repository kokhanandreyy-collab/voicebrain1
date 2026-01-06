import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _self_improve_memory_async
from app.models import LongTermMemory
import json

@pytest.mark.asyncio
async def test_self_improve_memory_flow():
    """Test that self-improvement correctly merges and archives memories."""
    user_id = "user123"
    db_mock = AsyncMock()
    
    # Mock memories
    m1 = MagicMock(spec=LongTermMemory)
    m1.id = "id1"
    m1.summary_text = "I like apples"
    m1.importance_score = 5.0
    
    m2 = MagicMock(spec=LongTermMemory)
    m2.id = "id2"
    m2.summary_text = "Apples are my favorite fruit"
    m2.importance_score = 6.0
    
    # Contradiction
    m3 = MagicMock(spec=LongTermMemory)
    m3.id = "id3"
    m3.summary_text = "I hate apples"
    m3.importance_score = 4.0

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [m1, m2, m3, MagicMock(), MagicMock()] # 5 items to pass minimum check
    db_mock.execute.return_value = mock_result
    
    # Mock AI response
    ai_resp = json.dumps({
        "merges": [{"ids": ["id1", "id2"], "summary": "Apples are my favorite fruit and I like them.", "score": 9.0}],
        "deletions": ["id3"]
    })
    
    with patch("workers.reflection_tasks.ai_service") as mock_ai, \
         patch("workers.reflection_tasks.AsyncSessionLocal", return_value=db_mock):
        
        mock_ai.get_chat_completion.return_value = ai_resp
        mock_ai.clean_json_response.return_value = ai_resp
        mock_ai.get_embedding.return_value = [0.1] * 1536
        
        await _self_improve_memory_async(user_id)
        
        # Check that we archived old ones
        # We expect 2 calls to update(LongTermMemory)
        assert db_mock.execute.call_count >= 3 # fetch + 2 updates
        assert db_mock.add.call_count == 1 # 1 new merged memory
        db_mock.commit.assert_called_once()
