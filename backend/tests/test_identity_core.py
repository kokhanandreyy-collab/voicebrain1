import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.models import LongTermMemory, User

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_identity_update_in_reflection(mock_db_session):
    """Test that generic reflection task updates user identify_summary."""
    
    user_id = "user_identity_test"
    
    # 1. Mock DB returns Notes then User
    mock_notes_res = MagicMock()
    mock_notes_res.scalars().all.return_value = [MagicMock(transcription_text="note", created_at="2024-01-01")]
    
    # User mock
    mock_user = User(id=user_id, identity_summary="old value")
    mock_user_res = MagicMock()
    mock_user_res.scalars().first.return_value = mock_user
    
    mock_db_session.execute.side_effect = [mock_notes_res, mock_user_res]
    
    # 2. Mock AI Logic
    json_resp = '{"summary": "Test Summary", "identity_summary": "NEW IDENTITY PROFILED", "importance_score": 8.0}'
    
    with patch("workers.reflection_tasks.ai_service") as mock_ai, \
         patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db_session # Context manager mock
         mock_ai.get_chat_completion = AsyncMock(return_value=json_resp)
         mock_ai.clean_json_response.return_value = json_resp
         mock_ai.get_embedding = AsyncMock(return_value=[0.1] * 1536)
         
         await _process_reflection_async(user_id)
         
         # 3. Assertions
         assert mock_user.identity_summary == "NEW IDENTITY PROFILED"
         assert mock_db_session.commit.called
         
@pytest.mark.asyncio
async def test_analyze_core_injects_identity():
    """Test AnalyzeCore injecting identity_summary into call context."""
    from app.core.analyze_core import analyze_core
    from app.models import Note, User
    
    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    
    user = User(id="u1", bio="My Bio", identity_summary="CORE IDENTITY")
    note = Note(id="n1", transcription_text="Hello world", user_id="u1")
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag:
         
         mock_rag.build_hierarchical_context = AsyncMock(return_value="RAG Context")
         mock_ai.analyze_text = AsyncMock(return_value={"title": "Analyzed", "summary": "X"})
         mock_rag.embed_note = AsyncMock()
         mock_memory.get_history = AsyncMock(return_value=[])
         mock_memory.add_action = AsyncMock()
         
         await analyze_core.analyze_step(note, user, mock_db, mock_memory)
         
         # Verification
         _, kwargs = mock_ai.analyze_text.call_args
         context_passed = kwargs.get("user_context", "")
         assert "My Bio" in context_passed
         assert "User Identity (Core Traits): CORE IDENTITY" in context_passed
