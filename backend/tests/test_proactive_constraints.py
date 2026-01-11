import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import User, LongTermMemory
from tasks.proactive import _trigger_proactive_reminders_async
import json
import datetime

@pytest.mark.asyncio
async def test_proactive_constraints():
    """
    Test proactive reminders:
    1. Skip if score <= 7
    2. Skip if disabled in settings
    3. Send if score > 7 and enabled
    """
    # Setup
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    # Mock User
    user = User(id="u1", telegram_chat_id="123", email="test@test.com", adaptive_preferences={"enable_proactive": True})
    user.last_note_date = datetime.datetime.now(datetime.timezone.utc)
    
    # Mock Memories
    mem1 = LongTermMemory(id="m1", user_id="u1", summary_text="Big Goal", importance_score=9.0, created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7))
    
    # Mock DB Query Results
    # 1. Users
    mock_users_res = MagicMock()
    mock_users_res.scalars.return_value.all.return_value = [user]
    
    # 2. Memories
    mock_mem_res = MagicMock()
    mock_mem_res.scalars.return_value.all.return_value = [mem1]
    
    # 3. Graph
    mock_graph_res = MagicMock()
    mock_graph_res.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_users_res, mock_mem_res, mock_graph_res, mock_mem_res, mock_graph_res] # Sequence for multiple runs or simple one
    
    # Case 1: High Relevance -> Send
    mock_json_high = json.dumps({"question": "How is the goal?", "relevance_score": 8})
    
    with patch("tasks.proactive.AsyncSessionLocal") as mock_session_cls, \
         patch("tasks.proactive.ai_service.get_chat_completion", new_callable=AsyncMock) as mock_ai, \
         patch("tasks.proactive.bot") as mock_bot:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         mock_ai.return_value = mock_json_high
         # Ensure send_message is async
         mock_bot.send_message = AsyncMock()
         
         await _trigger_proactive_reminders_async()
         
         # Result: Sent
         assert mock_bot.send_message.call_count == 1
         assert "How is the goal?" in mock_bot.send_message.call_args[1]["text"]

@pytest.mark.asyncio
async def test_proactive_low_relevance():
    # Setup
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    user = User(id="u1", telegram_chat_id="123", adaptive_preferences={"enable_proactive": True})
    user.last_note_date = datetime.datetime.now(datetime.timezone.utc)
    mock_users_res = MagicMock()
    mock_users_res.scalars.return_value.all.return_value = [user]
    
    mem1 = LongTermMemory(summary_text="Mundane thing", importance_score=8.0, created_at=datetime.datetime.now(datetime.timezone.utc))
    mock_mem_res = MagicMock()
    mock_mem_res.scalars.return_value.all.return_value = [mem1]
    
    mock_graph_res = MagicMock()
    mock_graph_res.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_users_res, mock_mem_res, mock_graph_res]
    
    # Case 2: Low Relevance -> Skip
    mock_json_low = json.dumps({"question": "Whatever", "relevance_score": 5})
    
    with patch("tasks.proactive.AsyncSessionLocal") as mock_session_cls, \
         patch("tasks.proactive.ai_service.get_chat_completion", new_callable=AsyncMock) as mock_ai, \
         patch("tasks.proactive.bot") as mock_bot:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         mock_ai.return_value = mock_json_low
         mock_bot.send_message = AsyncMock()
         
         await _trigger_proactive_reminders_async()
         
         # Result: Not Sent
         mock_bot.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_proactive_disabled_setting():
    # Setup
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    # Disabled in settings
    user = User(id="u1", telegram_chat_id="123", adaptive_preferences={"enable_proactive": False})
    user.last_note_date = datetime.datetime.now(datetime.timezone.utc)
    
    mock_users_res = MagicMock()
    mock_users_res.scalars.return_value.all.return_value = [user]
    
    mock_mem_res = MagicMock()
    mock_mem_res.scalars.return_value.all.return_value = [] # Shouldn't reach here anyway?
    
    mock_db.execute.side_effect = [mock_users_res]
    
    with patch("tasks.proactive.AsyncSessionLocal") as mock_session_cls, \
         patch("tasks.proactive.ai_service.get_chat_completion", new_callable=AsyncMock) as mock_ai, \
         patch("tasks.proactive.bot") as mock_bot:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         mock_bot.send_message = AsyncMock()
         
         await _trigger_proactive_reminders_async()
         
         # Result: AI not called, Sent not called
         mock_ai.assert_not_called()
         mock_bot.send_message.assert_not_called()
