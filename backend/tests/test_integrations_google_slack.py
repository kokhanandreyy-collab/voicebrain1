import pytest
import datetime
from unittest.mock import MagicMock, AsyncMock, patch, call
from app.models import Integration, Note
from app.services.integrations.google_calendar import GoogleCalendarIntegration
from app.services.integrations.slack import SlackIntegration

# --- Fixtures ---

@pytest.fixture
def google_integration_service():
    return GoogleCalendarIntegration()

@pytest.fixture
def slack_integration_service():
    return SlackIntegration()

@pytest.fixture
def mock_note_calendar():
    return Note(
        id="n_cal",
        title="Meeting with Client",
        summary="Discuss project details.",
        transcription_text="Let's meet tomorrow at 10am.",
        calendar_events=[
            {"title": "Client Meeting", "date": "2025-01-01", "time": "10:00"}
        ]
    )

@pytest.fixture
def mock_note_slack():
    return Note(
        id="n_slack",
        title="Important Update",
        summary="Released version 2.0.",
        action_items=["Check logs", "Notify team"],
        ai_analysis={"explicit_folder": "#announcements"}
    )

@pytest.fixture
def mock_integration_google():
    return Integration(
        id="i_google",
        provider="google_calendar",
        access_token="valid_token",
        refresh_token="ref_token",
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    )

@pytest.fixture
def mock_integration_slack():
    return Integration(
        id="i_slack",
        provider="slack",
        access_token="xoxb-token",
        config={"target_channel_id": "#general"}
    )

# --- Google Calendar Tests ---

@pytest.mark.asyncio
async def test_google_sync_event_basic(google_integration_service, mock_note_calendar, mock_integration_google, db_session):
    # Mock Aiogoogle context manager
    # We must patch where it's imported: app.services.integrations.google_calendar
    
    msg_mock = MagicMock()
    # Mocking Aiogoogle() instance
    mock_aiogoogle_instance = MagicMock()
    mock_aiogoogle_instance.__aenter__ = AsyncMock(return_value=mock_aiogoogle_instance)
    mock_aiogoogle_instance.__aexit__ = AsyncMock(return_value=None) 
    
    # Mock discover
    mock_cal_v3 = MagicMock()
    mock_aiogoogle_instance.discover = AsyncMock(return_value=mock_cal_v3)
    
    # Mock as_user
    mock_aiogoogle_instance.as_user = AsyncMock()
    # Side effects for as_user calls: 
    # 1. List (empty)
    # 2. Insert (success)
    mock_aiogoogle_instance.as_user.side_effect = [
        {"items": []}, 
        {"id": "evt_1"}
    ]

    with patch("app.services.integrations.google_calendar.Aiogoogle", return_value=mock_aiogoogle_instance):
        await google_integration_service.sync(mock_integration_google, mock_note_calendar, db_session)

        mock_aiogoogle_instance.discover.assert_called_with('calendar', 'v3')
        mock_cal_v3.events.list.assert_called_once()
        mock_cal_v3.events.insert.assert_called_once()
        
        args = mock_cal_v3.events.insert.call_args[1]
        assert args['json']['summary'] == "Client Meeting"

@pytest.mark.asyncio
async def test_google_sync_conflict_detected(google_integration_service, mock_note_calendar, mock_integration_google, db_session):
    mock_aiogoogle_instance = MagicMock()
    mock_aiogoogle_instance.__aenter__ = AsyncMock(return_value=mock_aiogoogle_instance)
    mock_aiogoogle_instance.__aexit__ = AsyncMock(return_value=None) 
    mock_cal_v3 = MagicMock()
    mock_aiogoogle_instance.discover = AsyncMock(return_value=mock_cal_v3)
    
    mock_aiogoogle_instance.as_user = AsyncMock()
    # 1. List (Conflict)
    # 2. Insert
    mock_aiogoogle_instance.as_user.side_effect = [
        {"items": [{"summary": "Existing"}]}, 
        {"id": "evt_2"}
    ]
    
    with patch("app.services.integrations.google_calendar.Aiogoogle", return_value=mock_aiogoogle_instance):
        await google_integration_service.sync(mock_integration_google, mock_note_calendar, db_session)
        
        args = mock_cal_v3.events.insert.call_args[1]
        assert "[CONFLICT]" in args['json']['summary']

@pytest.fixture
def mock_http_client():
    from infrastructure.http_client import http_client
    mock_robust = MagicMock()
    mock_robust.post = AsyncMock()
    # Ensure nested calls like client.post work
    http_client.client = mock_robust
    return mock_robust

@pytest.mark.asyncio
async def test_google_token_refresh(google_integration_service, mock_integration_google, db_session, mock_http_client):
    mock_integration_google.expires_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
    
    # Configure mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}
    mock_http_client.post.return_value = mock_resp
    
    with patch("app.core.security.encrypt_token", side_effect=lambda x: x.encode()), \
         patch("app.core.security.decrypt_token", side_effect=lambda x: x.decode()):
         
        await google_integration_service.ensure_token_valid(mock_integration_google, db_session)
        
        # Verify call made
        mock_http_client.post.assert_called()
        
        assert mock_integration_google.auth_token == "new_token"
        assert mock_integration_google.expires_at > datetime.datetime.now(datetime.timezone.utc)
        db_session.add.assert_called()

# --- Slack Tests ---

@pytest.mark.asyncio
async def test_slack_sync_success(slack_integration_service, mock_note_slack, mock_integration_slack):
    with patch("app.services.integrations.slack.AsyncWebClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.chat_postMessage = AsyncMock(return_value={"ok": True})
        
        await slack_integration_service.sync(mock_integration_slack, mock_note_slack)
        
        # Verify Channel resolution
        # Note has explicit folder #announcements
        client_instance.chat_postMessage.assert_called_once()
        args = client_instance.chat_postMessage.call_args[1]
        assert args["channel"] == "#announcements"
        
        # Verify Blocks
        blocks = args["blocks"]
        assert any("Important Update" in b.get("text", {}).get("text", "") for b in blocks if "text" in b)
        assert any("Action Items" in b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section")

@pytest.mark.asyncio
async def test_slack_sync_fallback_channel(slack_integration_service, mock_note_slack, mock_integration_slack):
    # Remove explicit folder from note
    mock_note_slack.ai_analysis = {}
    # Integ has config #general
    
    with patch("app.services.integrations.slack.AsyncWebClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.chat_postMessage = AsyncMock(return_value={"ok": True})
        
        await slack_integration_service.sync(mock_integration_slack, mock_note_slack)
        
        args = client_instance.chat_postMessage.call_args[1]
        assert args["channel"] == "#general"

@pytest.mark.asyncio
async def test_slack_retry_logic(slack_integration_service, mock_note_slack, mock_integration_slack):
    with patch("app.services.integrations.slack.AsyncWebClient") as MockClient:
        client_instance = MockClient.return_value
        
        # First call fails with "invalid_auth", Second succeeds
        client_instance.chat_postMessage = AsyncMock(side_effect=[
            Exception("invalid_auth error"), 
            {"ok": True}
        ])
        
        # Mock ensure_token_valid (empty as it's not implemented fully in base/slack yet but called)
        slack_integration_service.ensure_token_valid = AsyncMock()
        
        await slack_integration_service.sync(mock_integration_slack, mock_note_slack)
        
        assert client_instance.chat_postMessage.call_count == 2
        slack_integration_service.ensure_token_valid.assert_called_once()
