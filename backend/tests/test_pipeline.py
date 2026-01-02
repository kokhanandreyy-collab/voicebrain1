import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.pipeline import NotePipeline
from app.models import Note, NoteStatus

@pytest.mark.asyncio
async def test_pipeline_flow():
    # Setup Mocks
    mock_db = AsyncMock()
    mock_note = Note(id="test_note_1", status=NoteStatus.PENDING, user_id="user1")
    
    # Mock DB execution
    async def mock_execute(query):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_note
        return mock_result
    
    mock_db.execute.side_effect = mock_execute
    
    # Mock Core Services
    with patch("app.core.pipeline.AsyncSessionLocal", return_value=mock_db), \
         patch("app.core.pipeline.audio_processor") as mock_audio, \
         patch("app.core.pipeline.intent_service") as mock_intent, \
         patch("app.core.pipeline.sync_service") as mock_sync:
         
         # Configure return values for services
         mock_audio.process_audio.return_value = ("Transcribed Text", 60)
         
         pipeline = NotePipeline()
         await pipeline.process("test_note_1")
         
         # Assertions
         
         # 1. Transcribe Called
         mock_audio.process_audio.assert_called_once()
         assert mock_note.transcription_text == "Transcribed Text"
         assert mock_note.duration_seconds == 60
         
         # 2. Analyze Called
         mock_intent.analyze_note.assert_called_once()
         
         # 3. Sync Called (since mock_intent updates status to analyzed in real life, but here we mock it)
         # Note: My pipeline implementation calls services sequentially if status checks pass.
         # But mock_intent.analyze_note is mocked, so it WON'T update status to ANALYZED automatically unless side_effect does it.
         # The pipeline logic manually sets status after service call?
         # Let's check pipeline.py:
         # _run_analyze_stage:
         #    await intent_service.analyze_note(...)
         #    note.status = NoteStatus.ANALYZED
         # So yes, pipeline updates status.
         
         # However, pipeline status checks are sequential in one `process` run.
         # Stage 1 runs if PENDING. It does run. Sets PROCESSING. Then transcription set.
         # Stage 2 runs if PROCESSING or transcription present. It runs. Sets ANALYZED.
         # Stage 3 runs if ANALYZED. It runs. Sets COMPLETED.
         
         mock_sync.sync_note.assert_called_once()
         assert mock_note.status == NoteStatus.COMPLETED

@pytest.mark.asyncio
async def test_pipeline_idempotency():
    # Setup Mocks
    mock_db = AsyncMock()
    # Note already analyzed
    mock_note = Note(
        id="test_note_2", 
        status=NoteStatus.ANALYZED, 
        user_id="user1", 
        transcription_text="Exists",
        ai_analysis={"intent": "test"}
    )
    
    async def mock_execute(query):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_note
        return mock_result
    
    mock_db.execute.side_effect = mock_execute
    
    with patch("app.core.pipeline.AsyncSessionLocal", return_value=mock_db), \
         patch("app.core.pipeline.audio_processor") as mock_audio, \
         patch("app.core.pipeline.intent_service") as mock_intent, \
         patch("app.core.pipeline.sync_service") as mock_sync:
         
         pipeline = NotePipeline()
         await pipeline.process("test_note_2")
         
         # Assert 1 & 2 skipped
         mock_audio.process_audio.assert_not_called()
         mock_intent.analyze_note.assert_not_called()
         
         # Assert 3 run
         mock_sync.sync_note.assert_called_once()
         assert mock_note.status == NoteStatus.COMPLETED
