import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.tasks_service import tasks_service
from app.models import Note

@pytest.mark.asyncio
async def test_extract_task_details():
    """Verify task details extraction from voice text."""
    voice_text = "Remind me to call John tomorrow morning every Monday"
    mock_json = {
        "title": "Call John",
        "due_date": "2025-12-30T09:00:00",
        "recurring": "Every Monday",
        "note": "Call John tomorrow morning every Monday"
    }
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(mock_json)
        details = await tasks_service.extract_task_details(voice_text)
        assert details["title"] == "Call John"
        assert details["recurring"] == "Every Monday"

@pytest.mark.asyncio
async def test_create_or_update_reminder_flow():
    """Verify full task creation flow."""
    user_id = "u1"
    note_id = "n1"
    text = "Buy milk at 6pm"
    
    with patch.object(tasks_service, "extract_task_details", new_callable=AsyncMock) as mock_ext, \
         patch("app.services.integrations.tasks_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
        
        mock_ext.return_value = {"title": "Buy milk", "due_date": "2025-12-29T18:00:00", "recurring": None}
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        mock_note = MagicMock(spec=Note)
        mock_res_sim = MagicMock()
        mock_res_sim.scalars.return_value.all.return_value = [] # No similar tasks
        
        mock_res_note = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
        
        result = await tasks_service.create_or_update_reminder(user_id, note_id, text, provider="google_tasks")
        assert "Created google_tasks reminder" in result
        assert mock_note.reminder_id is not None
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_connect_tasks():
    """Verify OAuth connection placeholders."""
    with patch("app.services.integrations.tasks_service.AsyncSessionLocal") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        res = await tasks_service.connect_apple("u1", "code123")
        assert "Connected to Apple Reminders" in res
        assert mock_session.commit.called
