import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.analyze_core import AnalyzeCore
from app.models import Note, User

@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.close = AsyncMock()
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    return mock

@pytest.mark.asyncio
async def test_adaptive_memory_flow(mock_db_session):
    # Setup
    user = User(id="u1", adaptive_preferences={"old_key": "val"})
    note = Note(id="n1", user_id="u1", transcription_text="Context")
    
    mock_ai = AsyncMock()
    # Mock analysis response having adaptive_update and clarifying_question
    mock_ai.analyze_text = AsyncMock(return_value={
        "title": "Title",
        "adaptive_update": {"new_key": "new_val"},
        "ask_clarification": "What is X?"
    })
    
    # Needs rag_service mock too
    mock_rag = AsyncMock()
    mock_rag.build_hierarchical_context = AsyncMock(return_value="Context")
    mock_rag.embed_note = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service", mock_ai), \
         patch("app.core.analyze_core.rag_service", mock_rag):
         
         core = AnalyzeCore()
         await core.analyze_step(note, user, mock_db_session, AsyncMock())
         
         # Assert prompt injection
         call_kwargs = mock_ai.analyze_text.call_args.kwargs
         user_context = call_kwargs["user_context"]
         assert "old_key" in user_context # Injected existing prefs
         assert "Adaptive Preferences (Learned):" in user_context
         
         # Assert update (Merging)
         # Note: In strict SQLAlchemy, user.adaptive_preferences might need to be reassigned to trigger change detection, 
         # but our logic does user.adaptive_preferences = ...
         assert user.adaptive_preferences["new_key"] == "new_val"
         assert user.adaptive_preferences["old_key"] == "val"
         
         # Assert clarifying question in action items
         assert note.action_items is not None
         assert any("Clarification Needed: What is X?" in str(item) for item in note.action_items)
