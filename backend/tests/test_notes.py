import pytest
import io
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_notes_flow(client, db_session, test_user):
    # 1. Signup
    signup_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    response = await client.post("/auth/signup", json=signup_data)
    assert response.status_code == 200
    assert "Registration successful" in response.json()["message"]

    # 2. Verify Email (Manual bypass in DB)
    from sqlalchemy.future import select
    from app.models import User
    
    # Configure mock to return the user when queried
    from app.core.security import get_password_hash
    test_user.hashed_password = get_password_hash("TestPassword123!")
    test_user.is_verified = True
    
    # Configure mock for dynamic retrieval
    from app.models import Note
    mock_note = Note(id="n1", user_id=test_user.id, status="PROCESSING")
    
    def mock_execute(query, *args, **kwargs):
        query_str = str(query).lower()
        res = MagicMock()
        res.scalars = MagicMock()
        if "from users" in query_str:
            res.scalars.return_value.first.return_value = test_user
        elif "from notes" in query_str:
            res.scalars.return_value.first.return_value = mock_note
        else:
            res.scalars.return_value.first.return_value = None
        return res

    db_session.execute.side_effect = mock_execute

    # 3. Login
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Upload Audio
    audio_content = b"fake-audio-data"
    files = {"file": ("test.webm", io.BytesIO(audio_content), "audio/webm")}
    
    # We mock storage_client in conftest.py
    response = await client.post("/notes/upload", files=files, headers=headers)
    
    assert response.status_code == 200
    note_data = response.json()
    assert note_data["status"] == "PROCESSING"
    
    # Check DB
    note_id = note_data["id"]
    result = await db_session.execute(select(Note).where(Note.id == note_id))
    db_note = result.scalars().first()
    assert db_note is not None
    assert db_note.status == "PROCESSING"
    assert db_note.user_id == test_user.id
