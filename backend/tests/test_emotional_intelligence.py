import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.analyze_core import analyze_core
from app.models import Note, User
import datetime

@pytest.mark.asyncio
async def test_emotional_memory_history_update():
    """Test that mood is extracted and saved to user.emotion_history."""
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.id = "note_1"
    note.user_id = "user_1"
    note.transcription_text = "I am so happy today!"
    note.action_items = []
    
    user = MagicMock(spec=User)
    user.id = "user_1"
    user.emotion_history = []
    user.bio = ""
    user.identity_summary = ""
    user.adaptive_preferences = {}
    user.target_language = "Original"

    memory_service = AsyncMock()
    memory_service.get_history.return_value = []

    # Mock AI response
    ai_analysis = {
        "title": "Happy Day",
        "summary": "The user is happy.",
        "mood": "positive",
        "empathetic_comment": "I'm glad to hear you're having a great day!",
        "action_items": []
    }

    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.track_cache_miss"):
        
        mock_ai.analyze_text.return_value = ai_analysis
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_rag.build_hierarchical_context.return_value = "Context"
        
        # Trigger analysis
        await analyze_core.analyze_step(note, user, db_mock, memory_service)
        
        # Verify history update
        assert len(user.emotion_history) == 1
        assert user.emotion_history[0]["mood"] == "positive"
        assert "note_id" in user.emotion_history[0]
        
        # Verify empathetic comment was applied to the note
        # Note: empathetic_comment is stored in note.ai_analysis
        assert note.ai_analysis.empathetic_comment == "I'm glad to hear you're having a great day!"

@pytest.mark.asyncio
async def test_emotional_context_injection():
    """Test that the previous mood is injected into the next analysis prompt."""
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.transcription_text = "Still doing good."
    
    user = MagicMock(spec=User)
    user.emotion_history = [{"mood": "frustrated", "date": "yesterday"}]
    user.bio = ""
    user.identity_summary = ""
    user.adaptive_preferences = {}
    
    memory_service = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.track_cache_miss"):
        
        mock_ai.analyze_text.return_value = {"mood": "neutral"}
        
        await analyze_core.analyze_step(note, user, db_mock, memory_service)
        
        # Get the call to analyze_text
        args, kwargs = mock_ai.analyze_text.call_args
        user_context = kwargs.get("user_context", "")
        
        # Check if frustrated mood was passed in context
        assert "User current mood: frustrated" in user_context
        assert "Be empathetic" in user_context
