import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async, _trigger_reflection_async, reflection_daily
from app.models import User, Note, LongTermMemory

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_reflection_process(mock_db_session):
    """Test individual reflection task."""
    user_id = "u1"
    
    # Mock Notes
    notes = [
        Note(id=f"n{i}", user_id=user_id, transcription_text=f"Note content {i}", created_at="2024-01-01") 
        for i in range(5)
    ]
    
    # Mock DB Execute Responses
    # 1. nodes_count
    mock_metric_1 = MagicMock()
    mock_metric_1.scalar.return_value = 10
    
    # 2. edges_count
    mock_metric_2 = MagicMock()
    mock_metric_2.scalar.return_value = 5
    
    # 3. Notes Fetch
    mock_notes_result = MagicMock()
    mock_notes_result.scalars().all.return_value = notes
    
    # 4. Cache Check (Miss)
    mock_cache_res = MagicMock()
    mock_cache_res.scalars().first.return_value = None
    
    # 5. User Fetch for Identity
    mock_user = User(id=user_id, identity_summary="")
    mock_user_result = MagicMock()
    mock_user_result.scalars().first.return_value = mock_user
    
    mock_db_session.execute.side_effect = [
        mock_metric_1, 
        mock_metric_2, 
        mock_notes_result, 
        mock_cache_res,
        mock_user_result
    ]
    
    # Mock AI Service
    with patch("workers.reflection_tasks.ai_service") as mock_ai, \
         patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db_session
         
         # Mock LLM Response
         json_resp = '{"summary": "Пользователь работал.", "identity_summary": "Деловой", "importance_score": 9.5, "confidence": 0.9, "source": "fact"}'
         mock_ai.get_chat_completion = AsyncMock(return_value=json_resp)
         mock_ai.clean_json_response.return_value = json_resp
         # Mock Embedding
         mock_ai.get_embedding = AsyncMock(return_value=[0.1] * 1536)
         mock_ai.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
         
         await _process_reflection_async(user_id)
         
         # Verify AI called
         mock_ai.get_chat_completion.assert_called()
         
         # Verify Save Memory
         assert mock_db_session.add.call_count >= 1
         
         # Find LongTermMemory in add calls
         memory_obj = None
         for call in mock_db_session.add.call_args_list:
             arg = call[0][0]
             if isinstance(arg, LongTermMemory):
                 memory_obj = arg
                 break
         
         assert memory_obj is not None, "LongTermMemory object was not added to session"
         assert memory_obj.confidence == 0.9
         assert memory_obj.source == "fact"
         
         # Verify User Identity Updated
         assert mock_user.identity_summary == "Деловой"

@pytest.mark.asyncio
async def test_reflection_trigger(mock_db_session):
    """Test daily trigger for active users."""
    
    # Mock Users
    users = [User(id="u1"), User(id="u2")]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = users
    mock_db_session.execute.return_value = mock_result
    
    with patch("workers.reflection_tasks.reflection_daily") as mock_task, \
         patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db_session
         
         await _trigger_reflection_async()
         
         # Verify task calls
         assert mock_task.delay.call_count == 2
         mock_task.delay.assert_any_call("u1")
         mock_task.delay.assert_any_call("u2")
