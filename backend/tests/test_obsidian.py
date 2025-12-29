import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.obsidian_service import obsidian_service
from app.models import Note

@pytest.mark.asyncio
async def test_obsidian_note_generation():
    """Verify markdown note generation with backlinks."""
    user_id = "u1"
    note_id = "n1"
    text = "Talking about productivity and Zettelkasten."
    vault_path = "/tmp/obsidian_vault"
    
    with patch("app.services.integrations.obsidian_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
         patch("app.services.integrations.obsidian_service.decrypt_token") as mock_decrypt, \
         patch("os.makedirs") as mock_mkdir, \
         patch("builtins.open", new_callable=MagicMock) as mock_open:
        
        # Setup mocks
        mock_decrypt.return_value = vault_path
        mock_ask.return_value = "Zettelkasten Productivity"
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        # Integration result
        mock_int = MagicMock()
        mock_int.obsidian_vault_path = b"encrypted"
        
        # Similar notes result
        mock_res_sim = MagicMock()
        mock_similar_note = MagicMock(spec=Note)
        mock_similar_note.title = "Second Brain"
        mock_res_sim.scalars.return_value.all.return_value = [mock_similar_note]
        
        # Note result
        mock_note = MagicMock(spec=Note)
        mock_res_note = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_int)))),
            mock_res_sim,
            mock_res_note
        ]
        
        # Handle the integration lookup mock carefully as it's a chained call in my code
        # Actually my code is integration = int_res.scalars().first()
        mock_int_res = MagicMock()
        mock_int_res.scalars.return_value.first.return_value = mock_int
        mock_session.execute.side_effect = [mock_int_res, mock_res_sim, mock_res_note]

        res = await obsidian_service.create_or_update_note(user_id, note_id, text)
        
        assert "Zettelkasten Productivity.md" in res
        assert mock_open.called
        # Check if backlinks were included
        write_calls = mock_open.return_value.__enter__.return_value.write.call_args_list
        content = "".join([call[0][0] for call in write_calls])
        assert "[[Second Brain]]" in content
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_obsidian_connect():
    """Verify vault path storage."""
    with patch("app.services.integrations.obsidian_service.AsyncSessionLocal") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        res = await obsidian_service.connect("u1", "/path/to/vault")
        assert res == "Connected to Obsidian vault"
        assert mock_session.commit.called
