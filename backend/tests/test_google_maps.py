import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.integrations.google_maps_service import google_maps_service
from app.models import Note, Integration

@pytest.mark.asyncio
async def test_extract_location():
    """Verify that location is extracted from voice text."""
    voice_text = "I need to go to 1600 Amphitheatre Parkway, Mountain View"
    
    with patch("app.services.ai_service.ai_service.ask_notes", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = "1600 Amphitheatre Parkway, Mountain View"
        
        location = await google_maps_service.extract_location(voice_text)
        assert location == "1600 Amphitheatre Parkway, Mountain View"
        mock_ask.assert_called_once()

@pytest.mark.asyncio
async def test_geocode_place():
    """Verify that geocoding returns place data."""
    place_name = "Googleplex"
    
    mock_response = {
        "candidates": [{
            "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
            "name": "Googleplex",
            "place_id": "ChIJ2eUgeAK6j4ARbn5u_w79uIs",
            "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}}
        }]
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = mock_response
        
        place_data = await google_maps_service.geocode_place(place_name)
        assert place_data["place_id"] == "ChIJ2eUgeAK6j4ARbn5u_w79uIs"
        assert "Mountain View" in place_data["formatted_address"]

@pytest.mark.asyncio
async def test_generate_route():
    """Verify navigation URL generation."""
    url = await google_maps_service.generate_route("New York", "Boston", mode="walking")
    assert "origin=New+York" in url.replace(" ", "+")
    assert "destination=Boston" in url.replace(" ", "+")
    assert "travelmode=walking" in url

@pytest.mark.asyncio
async def test_create_or_update_place_flow():
    """Verify full flow from extraction to DB update."""
    user_id = "user_1"
    note_id = "note_1"
    voice_text = "Met a friend at Starbucks on 5th Ave"
    
    with patch.object(google_maps_service, "extract_location", new_callable=AsyncMock) as mock_extract, \
         patch.object(google_maps_service, "geocode_place", new_callable=AsyncMock) as mock_geocode, \
         patch("app.services.integrations.google_maps_service.AsyncSessionLocal") as mock_db_session, \
         patch("app.services.ai_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed:
        
        mock_extract.return_value = "Starbucks on 5th Ave"
        mock_geocode.return_value = {
            "formatted_address": "700 5th Ave, New York, NY 10019",
            "place_id": "starbucks_id"
        }
        mock_embed.return_value = [0.1] * 1536
        
        # Mock DB
        mock_session = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_session
        
        # Mock Note Query
        mock_note = MagicMock(spec=Note)
        mock_note.id = note_id
        mock_note.user_id = user_id
        
        mock_res_note = MagicMock()
        mock_res_note.scalars.return_value.first.return_value = mock_note
        
        # Mock Similarity Query (no results)
        mock_res_sim = MagicMock()
        mock_res_sim.scalars.return_value.all.return_value = []
        
        mock_session.execute.side_effect = [mock_res_sim, mock_res_note]
        
        url = await google_maps_service.create_or_update_place(user_id, note_id, voice_text)
        
        assert "google.com/maps" in url
        assert "starbucks_id" in url
        assert mock_note.google_maps_url == url
        assert mock_session.commit.called
