import pytest
from unittest.mock import AsyncMock, patch
from shared.api_client import VoiceBrainAPIClient

@pytest.mark.asyncio
async def test_get_notes_success():
    # Mocking httpx.AsyncClient response
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1", "title": "Test Note"}]
        mock_request.return_value = mock_response

        client = VoiceBrainAPIClient(base_url="http://test", api_key="fake_key")
        notes = await client.get_notes()
        
        assert len(notes) == 1
        assert notes[0]["title"] == "Test Note"
        await client.close()

@pytest.mark.asyncio
async def test_ask_ai_stream_mock():
    client = VoiceBrainAPIClient(base_url="http://test", api_key="fake_key")
    
    with patch.object(client.client, "stream") as mock_stream:
        # Mocking an async context manager
        mock_stream_response = AsyncMock()
        mock_stream_response.aiter_text.return_value = ["Hello", " world"]
        mock_stream.return_value.__aenter__.return_value = mock_stream_response
        
        chunks = []
        async for chunk in client.ask_ai_stream("Hi"):
            chunks.append(chunk)
            
        assert "".join(chunks) == "Hello world"
        await client.close()
