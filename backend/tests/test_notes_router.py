import pytest
from app.models import Note
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_create_text_note(client, db_session, test_user):
    payload = {
        "title": "Test Title",
        "transcription_text": "This is a test note content.",
        "tags": ["test", "fastapi"]
    }
    
    # Mock note for response
    note = Note(
        id="new-note-uuid",
        user_id=test_user.id,
        title=payload["title"],
        transcription_text=payload["transcription_text"],
        tags=payload["tags"],
        created_at=datetime.now(timezone.utc),
        audio_url="",
        status="PENDING"
    )
    db_session.add = MagicMock()
    # Mock the return value of create_text_note's final return
    # Actually client.post will return the real thing. 
    # But db.refresh(new_note) must not crash.
    
    response = await client.post("/notes/create-text", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Title"
    assert data["user_id"] == test_user.id

@pytest.mark.asyncio
async def test_get_notes(client, db_session, test_user):
    note = Note(
        id="existing-note-uuid",
        user_id=test_user.id, 
        title="Existing Note", 
        transcription_text="Hello",
        created_at=datetime.now(timezone.utc),
        audio_url="",
        status="COMPLETED",
        action_items=[],
        tags=[]
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [note]
    db_session.execute.return_value = mock_result

    response = await client.get("/notes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(n["title"] == "Existing Note" for n in data)

@pytest.mark.asyncio
async def test_ask_ai(client, db_session, test_user, mock_ai_service):
    note = Note(
        id="context-note",
        user_id=test_user.id, 
        title="Reference", 
        transcription_text="Context info",
        created_at=datetime.now(timezone.utc)
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [note]
    db_session.execute.return_value = mock_result

    payload = {"question": "What is in my notes?"}
    response = await client.post("/notes/ask", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "Mock answer"

@pytest.mark.asyncio
async def test_delete_note(client, db_session, test_user):
    note = Note(id="to-delete-uuid", user_id=test_user.id, title="To Delete")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = note
    db_session.execute.return_value = mock_result
    
    response = await client.delete(f"/notes/{note.id}")
    # Check if it should be 204 or 200
    assert response.status_code in [200, 204]

@pytest.mark.asyncio
async def test_reply_to_clarification(client, db_session, test_user, mock_ai_service):
    note = Note(
        id="ref-note",
        user_id=test_user.id, 
        title="Ref Note", 
        transcription_text="Old context", 
        action_items=["Clarification Needed: What color?"],
        created_at=datetime.now(timezone.utc),
        audio_url=""
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = note
    db_session.execute.return_value = mock_result

    payload = {"answer": "Red"}
    response = await client.post(f"/notes/{note.id}/reply", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["transcription_text"] is not None
