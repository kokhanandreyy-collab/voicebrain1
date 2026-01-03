import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.analyze_core import AnalyzeCore
from app.models import Note, User
import json

@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    return mock

@pytest.fixture
def analyze_core():
    return AnalyzeCore()

@pytest.mark.asyncio
async def test_ask_clarification_phrase_detection(mock_db_session, analyze_core):
    """Test that it automatically detects 'not sure' phrases and triggers clarification."""
    user = User(id="u1", adaptive_preferences={})
    note = Note(id="n1", user_id="u1", transcription_text="Context")
    
    mock_ai = AsyncMock()
    # Mock AI returning 'not sure' in summary but NOT in ask_clarification field
    mock_ai.analyze_text = AsyncMock(return_value={
        "title": "Title",
        "summary": "I am not sure about the priority.",
        "action_items": ["Old item"]
    })
    
    mock_rag = AsyncMock()
    mock_rag.build_hierarchical_context = AsyncMock(return_value="RAG")
    mock_rag.embed_note = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service", mock_ai), \
         patch("app.core.analyze_core.rag_service", mock_rag):
         
         await analyze_core.analyze_step(note, user, mock_db_session, AsyncMock())
         
         # Check if clarification was triggered
         assert any("Clarification Needed:" in item for item in note.action_items)
         assert "AI is unsure about some details" in str(note.action_items[0])

@pytest.mark.asyncio
async def test_save_preference(mock_db_session, analyze_core):
    """Test that adaptive_update is merged into user preferences."""
    user = User(id="u1", adaptive_preferences={"p0": "urgent"})
    note = Note(id="n1", user_id="u1", transcription_text="Reply")
    
    mock_ai = AsyncMock()
    mock_ai.analyze_text = AsyncMock(return_value={
        "title": "Update",
        "adaptive_update": {"p1": "high"}
    })
    
    mock_rag = AsyncMock()
    mock_rag.build_hierarchical_context = AsyncMock(return_value="RAG")
    mock_rag.embed_note = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service", mock_ai), \
         patch("app.core.analyze_core.rag_service", mock_rag):
         
         await analyze_core.analyze_step(note, user, mock_db_session, AsyncMock())
         
         # Check merged preferences
         assert user.adaptive_preferences["p0"] == "urgent"
         assert user.adaptive_preferences["p1"] == "high"
         assert mock_db_session.execute.called # update statement

@pytest.mark.asyncio
async def test_prompt_include(mock_db_session, analyze_core):
    """Test that user's adaptive preferences are injected into the AI prompt."""
    user = User(id="u1", adaptive_preferences={"project_x": "confidential"})
    note = Note(id="n1", user_id="u1", transcription_text="Talk")
    
    mock_ai = AsyncMock()
    mock_ai.analyze_text = AsyncMock(return_value={"title": "T"})
    
    mock_rag = AsyncMock()
    mock_rag.build_hierarchical_context = AsyncMock(return_value="RAG")
    mock_rag.embed_note = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service", mock_ai), \
         patch("app.core.analyze_core.rag_service", mock_rag):
         
         await analyze_core.analyze_step(note, user, mock_db_session, AsyncMock())
         
         call_kwargs = mock_ai.analyze_text.call_args.kwargs
         user_context = call_kwargs["user_context"]
         assert "project_x" in user_context
         assert "confidential" in user_context
         assert "Adaptive Preferences (Learned)" in user_context
