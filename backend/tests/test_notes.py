import pytest
import io

@pytest.mark.asyncio
async def test_notes_flow(async_client, db_session):
    # 1. Signup
    signup_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = await async_client.post("/auth/signup", json=signup_data)
    assert response.status_code == 200
    assert "Registration successful" in response.json()["message"]

    # 2. Verify Email (Manual bypass in DB)
    from sqlalchemy.future import select
    from app.models import User
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalars().first()
    user.is_verified = True
    await db_session.commit()

    # 3. Login
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = await async_client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Upload Audio
    audio_content = b"fake-audio-data"
    files = {"file": ("test.webm", io.BytesIO(audio_content), "audio/webm")}
    
    # We mock storage_client in conftest.py
    response = await async_client.post("/notes/upload", files=files, headers=headers)
    
    assert response.status_code == 200
    note_data = response.json()
    assert note_data["status"] == "PROCESSING"
    assert note_data["title"] == "Processing..."
    
    # Check DB
    from app.models import Note
    note_id = note_data["id"]
    result = await db_session.execute(select(Note).where(Note.id == note_id))
    db_note = result.scalars().first()
    assert db_note is not None
    assert db_note.status == "PROCESSING"
    assert db_note.user_id == user.id
