import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.yandex_tasks_service import yandex_tasks_service
from app.models import Note

@pytest.mark.asyncio
async def test_yandex_tasks_extraction():
    """Verify task details extraction from voice text."""
    voice_text = "Купить продукты завтра в 18:00 каждый понедельник"
    mock_json = {
        "summary": "Купить продукты",
        "description": "Купить продукты завтра в 18:00 каждый понедельник",
        "due_date": "2025-12-31T18:00:00",
        "recurring": "weekly on monday"
    }
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(mock_json)
        details = await yandex_tasks_service.extract_task_details(voice_text)
        assert details["summary"] == "Купить продукты"
        assert details["recurring"] == "weekly on monday"

@pytest.mark.asyncio
async def test_create_or_update_yandex_task_flow():
    """Verify full Yandex Tasks creation flow."""
    user_id = "u1"
    note_id = "n1"
    text = "Сделать отчет до вечера"
    
    with patch.object(yandex_tasks_service, "extract_task_details", new_callable=AsyncMock) as mock_ext, \
         patch("app.services.integrations.yandex_tasks_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
        
        mock_ext.return_value = {"summary": "Сделать отчет", "description": text, "due_date": "2025-12-30T20:00:00", "recurring": None}
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        mock_note = MagicMock(spec=Note)
        mock_res_sim = MagicMock()
        mock_res_sim.scalars = MagicMock()
        mock_res_sim.scalars.return_value.first.return_value = None # No similar tasks
        
        mock_res_note = MagicMock()
        mock_res_note.scalars = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
        
        result = await yandex_tasks_service.create_or_update_task(user_id, note_id, text)
        assert "yandex_task_" in result
        assert mock_note.yandex_task_id == result
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_yandex_tasks_connect():
    """Verify Yandex Tasks connection logic."""
    with patch("app.services.integrations.yandex_tasks_service.AsyncSessionLocal") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_result = MagicMock()
        mock_result.scalars = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"access_token": "yandex_token_123"}
            
            res = await yandex_tasks_service.connect("u1", "code_abc")
            assert res == "Connected to Yandex Tasks"
            assert mock_session.commit.called
