import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.yandex_maps_service import yandex_maps_service
from app.models import Note

@pytest.mark.asyncio
async def test_yandex_extract_location():
    """Verify Yandex location extraction."""
    voice_text = "Check in at Red Square, Moscow"
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = "Red Square, Moscow"
        location = await yandex_maps_service.extract_location(voice_text)
        assert location == "Red Square, Moscow"

@pytest.mark.asyncio
async def test_yandex_geocode():
    """Verify Yandex geocoding logic."""
    place_name = "Red Square"
    mock_response = {
        "response": {
            "GeoObjectCollection": {
                "featureMember": [{
                    "GeoObject": {
                        "name": "Red Square",
                        "Point": {"pos": "37.621094 55.75363"},
                        "metaDataProperty": {
                            "GeocoderMetaData": {"text": "Russia, Moscow, Red Square"}
                        }
                    }
                }]
            }
        }
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = mock_response
        
        geo_data = await yandex_maps_service.geocode_place(place_name)
        assert geo_data["coords"] == "55.75363,37.621094" # Yandex returns lat,lon after our swap
        assert "Moscow" in geo_data["address"]

@pytest.mark.asyncio
async def test_yandex_route():
    """Verify Yandex route generation."""
    url = await yandex_maps_service.generate_route("Moscow", "Sochi", avoid_traffic=True)
    assert "rtext=Moscow~Sochi" in url
    assert "trfm=1" in url

@pytest.mark.asyncio
async def test_yandex_place_flow():
    """Verify full Yandex flow."""
    user_id = "u1"
    note_id = "n1"
    text = "Lunch at Cafe Pushkin"
    
    with patch.object(yandex_maps_service, "extract_location", new_callable=AsyncMock) as mock_ext, \
         patch.object(yandex_maps_service, "geocode_place", new_callable=AsyncMock) as mock_geo, \
         patch("app.services.integrations.yandex_maps_service.AsyncSessionLocal") as mock_db, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
        
        mock_ext.return_value = "Cafe Pushkin"
        mock_geo.return_value = {"coords": "55.760,37.604", "address": "Tverskoy Blvd, Moscow"}
        mock_embed.return_value = [0.1]*1536
        
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        mock_note = MagicMock(spec=Note)
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = mock_note
        
        mock_session.execute.side_effect = [MagicMock(), mock_res]
        
        url = await yandex_maps_service.create_or_update_place(user_id, note_id, text)
        assert "yandex.ru/maps" in url
        assert mock_note.yandex_maps_url == url
        assert mock_session.commit.called
