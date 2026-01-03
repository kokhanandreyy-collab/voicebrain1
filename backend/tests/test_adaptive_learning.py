import pytest
from unittest.mock import AsyncMock, patch
from app.core.analyze_core import analyze_core
from app.models import Note, User

@pytest.mark.asyncio
async def test_adaptive_learning_prompt_injection():
    """Test that adaptive learning instructions are injected into user bio/context."""
    
    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    user = User(id="u1", bio="Bio", identity_summary="Identity")
    note = Note(id="n1", transcription_text="Set priority to P0", user_id="u1")
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag:
         
         mock_rag.build_hierarchical_context.return_value = "CTX"
         mock_ai.analyze_text.return_value = {"title": "T"}
         
         await analyze_core.analyze_step(note, user, mock_db, mock_memory)
         
         _, kwargs = mock_ai.analyze_text.call_args
         context = kwargs.get("user_context", "")
         
         # Assert adaptive instruction is present
         assert "Adaptive Learning:" in context
         assert "Is P0 High Priority?" in context
         
         # Assert identity is present
         assert "User Identity (Core Traits): Identity" in context
