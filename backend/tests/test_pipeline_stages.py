import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import Note, NoteStatus, User
from app.services.pipeline.stages import PipelineStages

@pytest.mark.asyncio
async def test_transcribe_stage_success():
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.id = "note_1"
    note.user_id = "user_1"
    note.duration_seconds = 0
    
    user = MagicMock(spec=User)
    user.monthly_usage_seconds = 0
    
    # Mock DB return for user
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = user
    db_mock.execute.return_value = user_res

    with patch("app.services.pipeline.stages.audio_processor.process_audio", AsyncMock(return_value=("Transcribed text", 60.0))):
        await PipelineStages.transcribe(note, db_mock)
        
        assert note.transcription_text == "Transcribed text"
        assert note.duration_seconds == 60.0
        assert user.monthly_usage_seconds == 60.0
        assert db_mock.commit.called

@pytest.mark.asyncio
async def test_analyze_stage_success():
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.user_id = "user_1"
    note.ai_analysis = {}
    
    user = MagicMock(spec=User)
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = user
    db_mock.execute.return_value = user_res

    with patch("app.services.pipeline.stages.analyze_core.analyze_step", AsyncMock(return_value=({"intent": "task"}, True))):
        await PipelineStages.analyze(note, db_mock)
        
        assert note.status == NoteStatus.ANALYZED
        assert note.ai_analysis["_cache_hit"] is True
        assert db_mock.commit.called
