import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import Integration
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_get_integrations_config(client):
    response = await client.get("/integrations/config")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == "notion" for item in data)

@pytest.mark.asyncio
async def test_get_integrations_empty(client, db_session):
    # Mocking db_session.execute to return empty list
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    db_session.execute.return_value = mock_res
    
    response = await client.get("/integrations")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_create_integration(client, db_session, test_user):
    # Mock existing check to return None
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    integration_data = {
        "provider": "notion",
        "credentials": {"api_key": "secret_12345"}
    }
    
    response = await client.post("/integrations", json=integration_data)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "notion"
    assert data["masked_settings"]["api_key"] == "****2345"

@pytest.mark.asyncio
async def test_delete_integration(client, db_session, test_user):
    # Mock finding integration
    mock_int = Integration(id="i1", provider="notion", user_id=test_user.id)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_int
    db_session.execute.return_value = mock_res
    
    response = await client.delete("/integrations/notion")
    assert response.status_code == 204
    db_session.delete.assert_called_once()

@pytest.mark.asyncio
async def test_get_auth_url(client):
    from infrastructure.config import settings
    # We can't easily patch the instance settings used in the module globally if it's already imported
    # But let's try setting the attribute directly on the imported object if it's a singleton
    
    with patch.object(settings, "GOOGLE_CALENDAR_CLIENT_ID", "mock_client_id", create=True):
        response = await client.get("/integrations/google_calendar/auth-url")
        assert response.status_code == 200
        assert "url" in response.json()
        assert "accounts.google.com" in response.json()["url"]

@pytest.mark.asyncio
async def test_integration_callback_mock(client, db_session, test_user):
    # Mock existing check
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    callback_data = {
        "provider": "slack",
        "code": "mock_code_123"
    }
    
    response = await client.post("/integrations/callback", json=callback_data)
    assert response.status_code == 200
    assert response.json()["status"] == "connected"
    db_session.add.assert_called_once()

@pytest.mark.asyncio
async def test_connect_google_maps(client):
    with patch("app.services.integrations.google_maps_service.google_maps_service.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = "Connected"
        response = await client.post("/integrations/google-maps/connect?code=123")
        assert response.status_code == 200
        assert response.json()["status"] == "Connected"

@pytest.mark.asyncio
async def test_connect_readwise(client):
    with patch("app.services.integrations.readwise_service.readwise_service.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = "Connected"
        response = await client.post("/integrations/readwise/connect?token=abc")
        assert response.status_code == 200
        assert response.json()["status"] == "Connected"

@pytest.mark.asyncio
async def test_connect_2gis(client, db_session, test_user):
    # Mock session results
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    response = await client.post("/integrations/2gis/connect?token=t2gis")
    assert response.status_code == 200
    assert "2GIS" in response.json()["status"]
