import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.analyze_core import AnalyzeCore
from app.models import Note, User

@pytest.mark.asyncio
async def test_analyze_note_by_id_orchestration():
    """Verify that analyze_note_by_id correctly orchestrates fetching and analysis."""
    core = AnalyzeCore()
    db_mock = AsyncMock()
    
    note = MagicMock(spec=Note)
    note.id = "note_1"
    note.user_id = "user_1"
    note.transcription_text = "test transcript"
    
    user = MagicMock(spec=User)
    
    # Mock DB executions
    db_mock.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=note)))), # Note
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=user)))), # User
    ]
    
    with patch.object(core, "analyze_step", AsyncMock(return_value=({"title": "Analyzed"}, False))) as mock_step:
        result = await core.analyze_note_by_id("note_1", db_mock, MagicMock())
        
        assert result["title"] == "Analyzed"
        assert note.status == "analyzed"
        assert db_mock.commit.called
        mock_step.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_step_context_building():
    """Verify that analyze_step correctly combines user context and RAG."""
    core = AnalyzeCore()
    db_mock = AsyncMock()
    
    note = MagicMock(spec=Note)
    note.transcription_text = "transcript"
    note.user_id = "user_1"
    
    user = MagicMock(spec=User)
    user.identity_summary = "Identity X"
    user.adaptive_preferences = {"pref": "Y"}
    user.bio = "Bio Z"
    user.target_language = "Russian"
    user.emotion_history = []
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.track_cache_miss"):
        
        mock_ai.generate_embedding.return_value = [0]*1536
        mock_ai.analyze_text.return_value = {"title": "T"}
        mock_rag.build_hierarchical_context.return_value = "RAG context"
        db_mock.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))) # Cache miss
        
        await core.analyze_step(note, user, db_mock, MagicMock())
        
        # Verify AI call arguments
        args, kwargs = mock_ai.analyze_text.call_args
        user_context = kwargs["user_context"]
        assert "Identity X" in user_context
        assert "pref" in user_context
        assert "Bio Z" in user_context
        assert kwargs["target_language"] == "Russian"
        assert kwargs["previous_context"] == "RAG context"
