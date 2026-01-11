
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.proactive import _trigger_proactive_reminders_async

@pytest.mark.asyncio
async def test_proactive_reminders_correct_context():
    """Test proactive reminder flow with correct context manager mock."""
    
    mock_db = AsyncMock()
    # Context manager setup
    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_db
    mock_ctx.__aexit__.return_value = None
    
    mock_user = AsyncMock()
    mock_user.id = "user1"
    mock_user.telegram_chat_id = "123"
    
    # Mock return values for DB execution
    # users query
    mock_res_users = MagicMock()
    mock_res_users.scalars.return_value.all.return_value = [mock_user]
    
    # memories query
    mock_res_memories = MagicMock()
    mock_memory = MagicMock()
    mock_memory.summary_text = "Planned to launch a rocket."
    mock_res_memories.scalars.return_value.all.return_value = [mock_memory]
    
    # rels query
    mock_res_rels = MagicMock()
    mock_res_rels.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [
        mock_res_users, # Fetch users
        mock_res_memories, # Fetch memories
        mock_res_rels # Fetch relations
    ]
    
    mock_bot = AsyncMock()
    # Ensure bool(mock_bot) is True (AsyncMock is truthy by default, but just in case)
    
    with patch("tasks.proactive.AsyncSessionLocal", return_value=mock_ctx), \
         patch("tasks.proactive.ai_service", new_callable=AsyncMock) as mock_ai, \
         patch("tasks.proactive.bot", mock_bot), \
         patch("tasks.proactive.logger") as mock_logger:
        
        # ai_service.get_chat_completion is async
        mock_ai.get_chat_completion.return_value = "How is the rocket launch going?"
        
        await _trigger_proactive_reminders_async()

        # Check for errors
        if mock_logger.error.called:
             print(f"Logger error called: {mock_logger.error.call_args}")
        
        # Ensure we actually called send_message
        assert mock_bot.send_message.called
        args = mock_bot.send_message.call_args
        assert args.kwargs['chat_id'] == "123"
