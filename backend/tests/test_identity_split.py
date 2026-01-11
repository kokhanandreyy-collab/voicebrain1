import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from tasks.reflection import _process_reflection_async
from app.models import User, Note
from app.core.analyze_core import analyze_core

@pytest.mark.asyncio
async def test_identity_split_reflection():
    """Test that reflection updates both stable and volatile identity."""
    user_id = "user-123"
    db_mock = AsyncMock()
    
    # Mock User
    user = User(id=user_id, stable_identity="", volatile_preferences={})
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = user
    
    # Mock Notes
    mock_notes = [Note(id="n1", transcription_text="I love coding in Python.", user_id=user_id)]
    notes_res = MagicMock()
    notes_res.scalars.return_value.all.return_value = mock_notes
    
    db_mock.execute.side_effect = [user_res, notes_res, MagicMock()] # User, Notes, Relation (empty)
    
    mock_ai = AsyncMock()
    # Return responses for 3 steps: Facts, Patterns, Relations
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5.0}', # Step 1: Facts
        '{"stable_identity": "Python lover", "volatile_preferences": {"mode": "coding"}}', # Step 2: Patterns
        '[]' # Step 3: Relations
    ]
    mock_ai.clean_json_response.side_effect = lambda x: x
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai):
        
        await _process_reflection_async(user_id)
        
        assert user.stable_identity == "Python lover"
        assert user.volatile_preferences["mode"] == "coding"
        db_mock.commit.assert_called()

@pytest.mark.asyncio
async def test_identity_prompt_injection():
    """Test that stable and volatile identity are injected correctly."""
    user = User(
        id="u1", 
        stable_identity="Communicates briefly", 
        volatile_preferences={"current_project": "VoiceBrain"}
    )
    note = Note(id="n1", transcription_text="Working on the RAG part", user_id="u1")
    db = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="context"):
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {}
        
        await analyze_core.analyze_step(note, user, db, AsyncMock())
        
        args, kwargs = mock_ai.analyze_text.call_args
        context = kwargs.get("user_context", "")
        
        assert "User Stable Identity" in context
        assert "Communicates briefly" in context
        assert '"current_project": "VoiceBrain"' in context
        assert "relevant to the current note's intent" in context
