import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.readwise_service import readwise_service
from app.models import Note

@pytest.mark.asyncio
async def test_readwise_highlight_extraction():
    """Verify highlight extraction via DeepSeek."""
    voice_text = "The only limit to our realization of tomorrow will be our doubts of today."
    mock_highlight = "The only limit to our realization of tomorrow will be our doubts of today."
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = mock_highlight
        result = await readwise_service.extract_highlight(voice_text)
        assert result == mock_highlight

@pytest.mark.asyncio
async def test_create_or_update_highlight_flow():
    """Verify Readwise highlight creation flow."""
    user_id = "u1"
    note_id = "n1"
    text = "Important quote about life."
    
    with patch.object(readwise_service, "extract_highlight", new_callable=AsyncMock) as mock_ext, \
         patch("app.services.integrations.readwise_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
        
        mock_ext.return_value = "Important quote"
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        mock_note = MagicMock(spec=Note)
        mock_res_sim = MagicMock()
        mock_res_sim.scalars.return_value.first.return_value = None
        
        mock_res_note = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
        
        result = await readwise_service.create_or_update_highlight(user_id, note_id, text)
        assert "hl_" in result
        assert mock_note.readwise_highlight_id is not None
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_readwise_connect():
    """Verify Readwise token connection logic."""
    with patch("app.services.integrations.readwise_service.AsyncSessionLocal") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        res = await readwise_service.connect("u1", "token123")
        assert res == "Connected to Readwise"
        assert mock_session.commit.called
