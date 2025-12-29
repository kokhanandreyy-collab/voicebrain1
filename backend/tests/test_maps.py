import pytest
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.maps_service import maps_service
from app.models import Note

@pytest.mark.asyncio
async def test_2gis_place_extraction():
    """Verify 2GIS place extraction and URL generation."""
    user_id = "u1"
    note_id = "n1"
    text = "Надо зайти в кофейню 'Академия' на проспекте Мира"
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
         patch("app.services.integrations.maps_service.AsyncSessionLocal") as mock_db:
        
        mock_ask.return_value = "кофейня Академия"
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        # Similar check
        mock_res_sim = MagicMock()
        mock_res_sim.scalars.return_value.first.return_value = None
        
        # Note update
        mock_note = MagicMock(spec=Note)
        mock_res_note = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
        
        result = await maps_service.create_or_update_place_2gis(user_id, note_id, text)
        assert "2gis.ru/search/кофейня%20Академия" in result
        assert mock_note.twogis_url == result
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_mapsme_kml_generation():
    """Verify Maps.me KML generation and file writing."""
    user_id = "u2"
    note_id = "n2"
    text = "Красивый вид на озеро в точке 55.75, 37.61"
    file_path = "/tmp/test_mapsme.kml"
    
    with patch("app.services.integrations.maps_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask, \
         patch("app.services.integrations.maps_service.decrypt_token") as mock_decrypt, \
         patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("os.makedirs") as mock_mkdir:
        
        mock_decrypt.return_value = file_path
        mock_ask.return_value = json.dumps({"name": "Озеро", "lat": 55.75, "lon": 37.61})
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        # Integration lookup
        mock_int = MagicMock()
        mock_int.mapsme_path = b"encrypted"
        mock_int_res = MagicMock()
        mock_int_res.scalars.return_value.first.return_value = mock_int
        
        # Note lookup
        mock_note = MagicMock(spec=Note)
        mock_note_res = MagicMock()
        mock_note_res.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [mock_int_res, mock_note_res]
        
        # Patch exists to false
        with patch("pathlib.Path.exists", return_value=False):
            res = await maps_service.create_or_update_place_mapsme(user_id, note_id, text)
            
            assert res == file_path
            assert mock_open.called
            write_content = mock_open.return_value.__enter__.return_value.write.call_args[0][0]
            assert "Озеро" in write_content
            assert "55.75" in write_content
            assert mock_session.commit.called
