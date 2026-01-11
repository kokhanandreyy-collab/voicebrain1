import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from tasks.proactive import _trigger_proactive_reminders_async
from app.models import User, LongTermMemory

@pytest.mark.asyncio
async def test_proactive_reminders_logic():
    """Test that proactive reminders find old memories and call AI."""
    db_mock = AsyncMock()
    
    # Mock user from 1 week ago
    mock_user = User(id="u1", email="test@ex.com", telegram_chat_id="123", last_note_date=datetime.datetime.now())
    user_res = MagicMock()
    user_res.scalars.return_value.all.return_value = [mock_user]
    
    # Mock memory from 1 week ago
    mock_memory = LongTermMemory(
        user_id="u1", 
        summary_text="Started learning Rust", 
        importance_score=8.5,
        created_at=datetime.datetime.now() - datetime.timedelta(days=7)
    )
    mem_res = MagicMock()
    mem_res.scalars.return_value.all.return_value = [mock_memory]
    
    # Mock graph relations (empty for simple test)
    graph_res = MagicMock()
    graph_res.scalars.return_value.all.return_value = []
    
    db_mock.execute.side_effect = [user_res, mem_res, graph_res]
    
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.return_value = "Как там твой Rust?"
    
    with patch("tasks.proactive.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.proactive.ai_service", mock_ai), \
         patch("tasks.proactive.bot") as mock_bot:
        
        await _trigger_proactive_reminders_async()
        
        # Verify AI was called with the memory context
        mock_ai.get_chat_completion.assert_called_once()
        args = mock_ai.get_chat_completion.call_args[0][0]
        assert any("learning Rust" in m["content"] for m in args if m["role"] == "user")
        
        # Verify bot sent the message
        mock_bot.send_message.assert_called_once()
        assert "Как там твой Rust?" in mock_bot.send_message.call_args[1]["text"]
        assert "proactive_yes" in str(mock_bot.send_message.call_args[1]["reply_markup"])
