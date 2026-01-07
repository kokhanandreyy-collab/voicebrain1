import pytest
from app.models import Note
from datetime import datetime, timezone
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_get_notes_pagination(client, db_session, test_user):
    # Setup mock data
    notes = [
        Note(
            id=f"note-{i}",
            user_id=test_user.id,
            title=f"Note {i}",
            transcription_text=f"Content {i}",
            created_at=datetime.now(timezone.utc),
            audio_url="",
            status="COMPLETED",
            tags=[],
            action_items=[]
        ) for i in range(5)
    ]
    
    # Mock count result
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 5
    
    # Mock items result
    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = notes[:2]
    
    # Mock integration status result
    mock_status_res = MagicMock()
    mock_status_res.all.return_value = []
    
    # Mock execute for count, items, and integration status
    db_session.execute.side_effect = [mock_count_res, mock_items_res, mock_status_res]

    response = await client.get("/notes?limit=2&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] == 5
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Note 0"
    assert data["items"][1]["title"] == "Note 1"

@pytest.mark.asyncio
async def test_get_notes_pagination_offset(client, db_session, test_user):
    # Setup mock data
    notes = [
        Note(
            id=f"note-{i}",
            user_id=test_user.id,
            title=f"Note {i}",
            transcription_text=f"Content {i}",
            created_at=datetime.now(timezone.utc),
            audio_url="",
            status="COMPLETED",
            tags=[],
            action_items=[]
        ) for i in range(5)
    ]
    
    # Mock count result
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 5
    
    # Mock items result (offset 2, limit 2)
    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = notes[2:4]
    
    # Mock integration status result
    mock_status_res = MagicMock()
    mock_status_res.all.return_value = []
    
    db_session.execute.side_effect = [mock_count_res, mock_items_res, mock_status_res]

    response = await client.get("/notes?limit=2&offset=2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Note 2"
    assert data["items"][1]["title"] == "Note 3"
