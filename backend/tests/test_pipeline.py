import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from app.models import Note, NoteStatus, User
from app.services.pipeline import pipeline

# Import modules to ensure they are attached to app.core
import app.core.sync_service
import app.core.audio
import app.core.analyze_core
import app.core.bot

@pytest.mark.asyncio
async def test_pipeline_full_flow(db_session, test_user, mock_celery):
    # Setup Note
    note = Note(
        id="note-uuid",
        user_id=test_user.id,
        title="Initial Title",
        status=NoteStatus.PENDING,
        audio_url="http://mock.com/audio.ogg",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    # Configure mock for multiple execute calls
    async def mock_execute(query):
        mock_result = MagicMock()
        q_str = str(query).lower()
        if "from notes" in q_str:
             mock_result.scalars.return_value.first.return_value = note
             mock_result.scalars.return_value.all.return_value = [note]
        elif "from users" in q_str:
             mock_result.scalars.return_value.first.return_value = test_user
        return mock_result

    db_session.execute = AsyncMock(side_effect=mock_execute)

    # Mock stages
    with patch("app.core.audio.audio_processor.process_audio", AsyncMock(return_value=("Transcribed text", 10.0))), \
         patch("app.core.analyze_core.analyze_core.analyze_step", AsyncMock()) as mock_analyze, \
         patch("app.core.sync_service.sync_service.sync_note", AsyncMock()) as mock_sync, \
         patch("app.core.bot.bot", MagicMock()) as mock_bot:
        
        mock_bot.send_message = AsyncMock()
        
        await pipeline.process(note.id)
        
        # Verify stages were called
        await db_session.refresh(note)
        assert note.status == NoteStatus.COMPLETED
        assert note.transcription_text == "Transcribed text"
        assert note.duration_seconds == 10.0
        assert mock_analyze.called
        assert mock_sync.called

@pytest.mark.asyncio
async def test_pipeline_error_handling(db_session, test_user):
    note = Note(id="err-note-uuid", user_id=test_user.id, status=NoteStatus.PENDING, created_at=datetime.now(timezone.utc))
    # Configure mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = note
    db_session.execute = AsyncMock(return_value=mock_result)

    # Force error in transcription
    with patch("app.core.audio.audio_processor.process_audio", AsyncMock(side_effect=ValueError("Test Error"))):
        await pipeline.process(note.id)
        
        await db_session.refresh(note)
        assert note.status == NoteStatus.FAILED
        assert "Error: Test Error" in note.processing_step
