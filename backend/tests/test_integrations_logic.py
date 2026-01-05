import pytest
import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from app.models import Integration, Note
from app.services.integrations.notion import NotionIntegration

@pytest.fixture
def notion_integration():
    return NotionIntegration()

@pytest.fixture
def mock_note():
    return Note(
        id="n1",
        title="Project Alpha Discussion",
        summary="Discussed Alpha.",
        transcription_text="This is the full transcript.",
        ai_analysis={
            "intent": "meeting",
            "suggested_project": "Project Alpha",
            "entities": ["Alpha", "Beta"],
            "notion_properties": {
                "Priority": "High",
                "Status": "To Do"
            }
        },
        action_items=["Buy milk", "Call John"],
        created_at=datetime.datetime(2025, 1, 1, 12, 0, 0),
        tags=["work", "urgent"]
    )

@pytest.fixture
def mock_integration_model():
    return Integration(
        id="i1",
        provider="notion",
        access_token="fake_token",
        config={"database_id": "db_123"}
    )

@pytest.mark.asyncio
async def test_notion_sync_new_page(notion_integration, mock_note, mock_integration_model):
    # Mock Notion Client
    with patch("app.services.integrations.notion.AsyncClient") as MockClient:
        client_instance = MockClient.return_value
        
        # Mock Search Result (Empty -> Create New)
        client_instance.databases.query = AsyncMock(return_value={"results": []})
        client_instance.pages.create = AsyncMock(return_value={"id": "new_page_id"})
        
        await notion_integration.sync(mock_integration_model, mock_note)
        
        # Verify Search
        client_instance.databases.query.assert_called_once()
        args = client_instance.databases.query.call_args[1]
        assert args["database_id"] == "db_123"
        
        # Verify Create
        client_instance.pages.create.assert_called_once()
        create_kwargs = client_instance.pages.create.call_args[1]
        props = create_kwargs["properties"]
        
        assert "Name" in props
        assert props["Name"]["title"][0]["text"]["content"] == "Project Alpha Discussion"
        assert props["Priority"]["select"]["name"] == "High"
        assert props["Status"]["select"]["name"] == "To Do"
        assert "Tags" in props
        assert len(props["Tags"]["multi_select"]) == 2

@pytest.mark.asyncio
async def test_notion_sync_append_existing(notion_integration, mock_note, mock_integration_model):
    with patch("app.services.integrations.notion.AsyncClient") as MockClient:
        client_instance = MockClient.return_value
        
        # Mock Search Result (Found)
        client_instance.databases.query = AsyncMock(return_value={
            "results": [{"id": "existing_page_id"}]
        })
        client_instance.blocks.children.append = AsyncMock()
        
        await notion_integration.sync(mock_integration_model, mock_note)
        
        # Verify Append
        client_instance.blocks.children.append.assert_called_once()
        args = client_instance.blocks.children.append.call_args[1]
        assert args["block_id"] == "existing_page_id"
        assert len(args["children"]) > 0
        # Check for divider
        assert args["children"][0]["type"] == "divider"

@pytest.mark.asyncio
async def test_notion_sync_no_db_id(notion_integration, mock_note):
    bad_integration = Integration(id="i2", provider="notion", config={})
    
    with pytest.raises(ValueError, match="Notion Database ID not configured"):
        await notion_integration.sync(bad_integration, mock_note)
