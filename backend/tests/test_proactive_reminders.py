import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from app.models import User, LongTermMemory

@pytest.mark.asyncio
async def test_proactive_reminders_trigger():
    """Test that proactive reminders find relevant memories and call AI/Bot."""
    from tasks.proactive import _trigger_proactive_reminders_async
    
    mock_db = AsyncMock()
    
    # 1. Mock One User
    user = User(id="u1", telegram_chat_id="12345", last_note_date=datetime.now(timezone.utc))
    mock_user_res = MagicMock()
    mock_user_res.scalars.return_value.all.return_value = [user]
    
    # 2. Mock One Memory from last week
    memory = LongTermMemory(
        user_id="u1", 
        summary_text="Started a new project about kitchen renovation.",
        importance_score=9.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=7)
    )
    mock_mem_res = MagicMock()
    mock_mem_res.scalars.return_value.all.return_value = [memory]
    
    # DB Sequence
    mock_db.execute.side_effect = [mock_user_res, mock_mem_res]
    
    with patch("tasks.proactive.AsyncSessionLocal", return_value=mock_db), \
         patch("tasks.proactive.ai_service") as mock_ai, \
         patch("tasks.proactive.bot") as mock_bot:
             
        mock_ai.get_chat_completion = AsyncMock(return_value="Как продвигается ремонт кухни?")
        mock_bot.send_message = AsyncMock()
        
        await _trigger_proactive_reminders_async()
        
        # Verify AI was consulted
        mock_ai.get_chat_completion.assert_called_once()
        # Verify Telegram message was sent
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert "кухни" in kwargs["text"]
        assert "reply_markup" in kwargs
