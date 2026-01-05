import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.integrations.email import EmailIntegration
from app.models import Integration, Note, User
import datetime

@pytest.fixture
def email_integration_service():
    return EmailIntegration()

@pytest.fixture
def mock_integration_email():
    # Mock Integration with User loaded
    user = MagicMock(spec=User)
    user.email = "test@example.com"
    
    integ = MagicMock(spec=Integration)
    integ.user = user
    return integ

@pytest.fixture
def mock_note_email():
    return Note(
        id="n_email",
        title="Email Note",
        summary="Summary of email content.",
        action_items=["Buy milk"],
        transcription_text="Reminder to buy milk.",
        created_at=datetime.datetime(2025, 1, 1, 12, 0, 0),
        ai_analysis={}
    )

@pytest.mark.asyncio
async def test_email_sync_success(email_integration_service, mock_integration_email, mock_note_email):
    # Mock settings
    with patch("app.services.integrations.email.settings") as mock_settings, \
         patch("app.services.integrations.email.FastMail") as MockFastMail, \
         patch("app.services.integrations.email.MessageSchema") as MockMessageSchema:
        
        # Configure settings defaults
        mock_settings.SMTP_USER = "user"
        mock_settings.SMTP_PASSWORD = "password"
        mock_settings.SMTP_FROM = "noreply@voicebrain.app"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_HOST = "smtp.example.com"
        
        # Configure FastMail mock
        mock_fm_instance = MockFastMail.return_value
        mock_fm_instance.send_message = AsyncMock()
        
        await email_integration_service.sync(mock_integration_email, mock_note_email)
        
        mock_fm_instance.send_message.assert_called_once()
        
        # Verify MessageSchema construction
        MockMessageSchema.assert_called_once()
        kwargs = MockMessageSchema.call_args[1]
        
        assert kwargs["subject"] == "VoiceBrain Note: Email Note"
        assert "test@example.com" in kwargs["recipients"]
        assert "Email Note" in kwargs["body"]
        assert "Buy milk" in kwargs["body"]

@pytest.mark.asyncio
async def test_email_sync_extra_recipient(email_integration_service, mock_integration_email, mock_note_email):
    # Add explicit folder containing email
    mock_note_email.ai_analysis = {"explicit_folder": "boss@example.com"}
    
    with patch("app.services.integrations.email.settings") as mock_settings, \
         patch("app.services.integrations.email.FastMail") as MockFastMail, \
         patch("app.services.integrations.email.MessageSchema") as MockMessageSchema:
         
         mock_fm_instance = MockFastMail.return_value
         mock_fm_instance.send_message = AsyncMock()
         
         await email_integration_service.sync(mock_integration_email, mock_note_email)
         
         kwargs = MockMessageSchema.call_args[1]
         assert "boss@example.com" in kwargs["recipients"]
         assert "test@example.com" in kwargs["recipients"]

@pytest.mark.asyncio
async def test_email_sync_no_user_email(email_integration_service, mock_integration_email, mock_note_email):
    mock_integration_email.user.email = None
    
    with pytest.raises(Exception, match="User has no email address"):
        await email_integration_service.sync(mock_integration_email, mock_note_email)
