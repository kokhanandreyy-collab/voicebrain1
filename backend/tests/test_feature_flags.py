import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.models import User, Note, Integration
from app.core.sync_service import SyncService

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_feature_flags_default():
    """Test that new users have default flags enabled."""
    user = User()
    # Default is applied by SQLAlchemy on flush usually, but here checking model definition
    # In Pydantic/SQLAlchemy default arg:
    col_default = User.feature_flags.default.arg
    assert col_default == {"all_integrations": True}

@pytest.mark.asyncio
async def test_sync_service_skips_disabled_provider(mock_db):
    """Test that sync service skips integration if disabled in feature flags."""
    
    # Setup Data
    user = User(id="u1", feature_flags={"all_integrations": True, "notion_enabled": False})
    note = Note(id="n1", user_id="u1", user=user)
    
    # Integration that SHOULD be skipped
    integration_notion = Integration(provider="notion", user_id="u1", user=user)
    # Integration that SHOULD run
    integration_todoist = Integration(provider="todoist", user_id="u1", user=user)
    
    user_integrations = [integration_notion, integration_todoist]
    
    # Mock DB Query results
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = user_integrations
    mock_db.execute.return_value = mock_result
    
    # Mock Handlers (Celery Tasks)
    # We need to patch the imports inside sync_service or the delay calls
    # Since sync_service imports them inside the method, we patch 'app.core.sync_service.sync_tasks' etc?
    # Actually, sync_service imports from `workers.sync_tasks`.
    
    with patch("app.core.sync_service.sync_tasks") as mock_tasks_worker, \
         patch("app.core.sync_service.sync_readwise") as mock_readwise_worker: # Notion not in standard list in code snippet?
         
         # Wait, in the code snippet for sync_service (Step 780):
         # It checks specific providers. "notion" falls into `else: pass` or implicit generic?
         # The snippet had `elif integration.provider in ["apple_reminders", "google_tasks"]` etc.
         # "notion" wasn't explicitly handled in `sync_note` loop in step 780's file view! 
         # It falls to `else: pass`. So it wouldn't run anyway.
         # Let's use "readwise" as the skipped one ("readwise_enabled": False).
         
         user.feature_flags = {"all_integrations": True, "readwise_enabled": False}
         integration_readwise = Integration(provider="readwise", user_id="u1", user=user)
         integration_gmail = Integration(provider="gmail", user_id="u1", user=user)
         
         mock_result.scalars().all.return_value = [integration_readwise, integration_gmail]
         
         service = SyncService()
         
         # We need to verify `sync_readwise.delay` is NOT called
         # And `sync_email.delay` IS called (for gmail)
         
         with patch("app.core.sync_service.sync_email") as mock_email_worker, \
              patch("app.core.sync_service.sync_readwise") as mock_readwise_worker:
              
              await service.sync_note(note, mock_db)
              
              mock_readwise_worker.delay.assert_not_called()
              mock_email_worker.delay.assert_called_with(note.id, "gmail")

@pytest.mark.asyncio
async def test_sync_service_skips_all(mock_db):
    """Test global kill switch."""
    user = User(id="u1", feature_flags={"all_integrations": False})
    note = Note(id="n1", user_id="u1", user=user)
    integration = Integration(provider="gmail", user_id="u1", user=user)
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [integration]
    mock_db.execute.return_value = mock_result
    
    service = SyncService()
    
    with patch("app.core.sync_service.sync_email") as mock_email_worker:
        await service.sync_note(note, mock_db)
        mock_email_worker.delay.assert_not_called()
