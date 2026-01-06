import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from app.models import Note, User

@pytest.mark.asyncio
async def test_emotional_memory_history_update():
    """Test that emotion history is updated in User model after analysis."""
    from app.core.analyze_core import AnalyzeCore

    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    mock_memory.get_history.return_value = []
    
    # Setup User with existing history
    user = User(
        id="u1", 
        emotion_history=[{"mood": "Neutral", "date": "yesterday"}]
    )
    note = Note(id="n1", user_id="u1", transcription_text="I am feeling great!")

    with patch("app.core.analyze_core.ai_service") as mock_ai:
        # Mock AI returning positive mood and empathy
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {
            "title": "Happy Note",
            "mood": "Positive",
            "empathetic_comment": "Glad you're happy!",
            "intent": "note"
        }
        
        # scalars().first() -> None for cache
        mock_db.execute.return_value.scalars.return_value.first.return_value = None

        core = AnalyzeCore()
        await core.analyze_step(note, user, mock_db, mock_memory)
        
        # Verify history updated
        assert len(user.emotion_history) == 2
        assert user.emotion_history[-1]["mood"] == "Positive"
        assert "note_id" in user.emotion_history[-1]

@pytest.mark.asyncio
async def test_emotional_memory_context_injection():
    """Test that mood history is injected into context for following analysis."""
    from app.core.analyze_core import AnalyzeCore

    mock_db = AsyncMock()
    mock_memory = AsyncMock()
    mock_memory.get_history.return_value = []
    
    # User was frustrated
    user = User(
        id="u1", 
        emotion_history=[{"mood": "Frustrated", "date": "2026-01-01"}]
    )
    note = Note(id="n2", user_id="u1", transcription_text="Still having issues.")

    with patch("app.core.analyze_core.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {
            "title": "Continuing Issues",
            "mood": "Negative",
            "empathetic_comment": "I see you're still struggling—how can I help?",
            "intent": "task"
        }
        mock_db.execute.return_value.scalars.return_value.first.return_value = None

        core = AnalyzeCore()
        await core.analyze_step(note, user, mock_db, mock_memory)
        
        # Verify user_context passed to analyze_text contains 'Frustrated'
        args, kwargs = mock_ai.analyze_text.call_args
        context = kwargs.get("user_context", "")
        assert "Frustrated" in context
        assert "Instruction: The user was previously Frustrated" in context
