import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.email_service import email_service
from app.models import Note

@pytest.mark.asyncio
async def test_email_draft_generation():
    """Verify email draft content generation via DeepSeek."""
    voice_text = "Follow up with Sarah about the project launch on Friday."
    mock_json = {
        "subject": "Follow-up: Project Launch",
        "body": "Hi Sarah, just following up on our discussion about the project launch this Friday."
    }
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(mock_json)
        # Mocking generate_embedding for the RAG part inside create_or_update_draft
        with patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1]*1536
            
            with patch("app.services.integrations.email_service.AsyncSessionLocal") as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock sim_result and note_res
                mock_res_sim = MagicMock()
                mock_res_sim.scalars = MagicMock()
                mock_res_sim.scalars.return_value.first.return_value = None
                
                mock_note = MagicMock(spec=Note)
                mock_res_note = MagicMock()
                mock_res_note.scalars = MagicMock()
                mock_res_note.scalars.return_value.first.return_value = mock_note
                
                mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
                
                draft_id = await email_service.create_or_update_draft("u1", "n1", voice_text, provider="gmail")
                assert "draft_gmail" in draft_id
                assert mock_note.email_draft_id == draft_id
                assert mock_session.commit.called

@pytest.mark.asyncio
async def test_email_oauth_connect():
    """Verify email connection logic placeholders."""
    with patch("app.services.integrations.email_service.AsyncSessionLocal") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_result = MagicMock()
        mock_result.scalars = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Mock httpx for token exchange
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"access_token": "test_token"}
            
            res = await email_service.connect_gmail("u1", "code123")
            assert res == "Connected to Gmail"
            assert mock_session.commit.called
