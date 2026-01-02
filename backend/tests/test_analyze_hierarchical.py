import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.analyze_core import AnalyzeCore
from app.models import Note, User

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.mark.asyncio
async def test_hierarchical_context_integration(mock_db_session):
    """Test full context assembly in analyze_step."""
    
    # Setup
    analyzer = AnalyzeCore()
    user = User(id="u1", identity_summary="IdentityContent")
    note = Note(id="n1", user_id="u1", transcription_text="New Note")
    
    # Mock RAG Service
    with patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.ai_service") as mock_ai:
         
         # Mock hierarchical context return
         expected_context = "Short-term: ...\nRecent: ...\nLong-term: ..."
         mock_rag.build_hierarchical_context.return_value = expected_context
         
         # Mock AI response
         mock_ai.analyze_text.return_value = {
             "title": "Analyzed Title", 
             "summary": "Summary",
             "action_items": []
         }
         
         # Execute
         await analyzer.analyze_step(note, user, mock_db_session, memory_service=AsyncMock())
         
         # Verify build_hierarchical_context called
         mock_rag.build_hierarchical_context.assert_called_once()
         
         # Verify analyze_text called with correct context
         args = mock_ai.analyze_text.call_args
         kwargs = args.kwargs
         
         # Check User Context (Identity)
         assert "User Identity Core: IdentityContent" in kwargs['user_context']
         
         # Check Previous Context (Hierarchical)
         assert kwargs['previous_context'] == expected_context

@pytest.mark.asyncio
async def test_build_hierarchical_context(mock_db_session):
    """Test the RAG service logic directly."""
    from app.core.rag_service import rag_service
    
    note = Note(id="curr", user_id="u1", transcription_text="Query")
    
    # Mock DB for Short Term (Last 5)
    mock_notes = [Note(title=f"Old {i}", summary="Sum") for i in range(5)]
    mock_res = MagicMock()
    mock_res.scalars().all.return_value = mock_notes
    mock_db_session.execute.return_value = mock_res
    
    # Mock medium/long term internals if needed, or rely on empty returns if not mocked?
    # RAG service class methods `get_medium_term_context` and `get_long_term_memory` call DB too.
    # To test fully we need to mock those or mock the db calls they make.
    # Easiest is to mock the methods on the rag_service instance wrapper.
    
    with patch.object(rag_service, 'get_medium_term_context', return_value="MediumContent") as mock_med, \
         patch.object(rag_service, 'get_long_term_memory', return_value="LongContent") as mock_long:
         
         ctx = await rag_service.build_hierarchical_context(note, mock_db_session, None)
         
         assert "Short-term (Last 5 notes):" in ctx
         assert "Old 0" in ctx
         assert "MediumContent" in ctx
         assert "LongContent" in ctx
