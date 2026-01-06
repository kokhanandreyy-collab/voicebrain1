import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.analyze_core import analyze_core
from app.models import Note, User
import json

@pytest.mark.asyncio
async def test_adaptive_memory_extraction():
    """Test that AI extracts adaptive updates and saves them to user preferences."""
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.transcription_text = "Question: What is P0?\nAnswer: P0 means critical urgency."
    
    user = MagicMock(spec=User)
    user.id = "user_123"
    user.adaptive_preferences = {}
    user.bio = ""
    user.identity_summary = ""
    user.target_language = "Original"
    user.emotion_history = []
    
    # Mock AI response with adaptive_update
    ai_analysis = {
        "title": "Preference Update",
        "summary": "User defined P0.",
        "adaptive_update": {"P0": "critical urgency"},
        "mood": "neutral"
    }
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.track_cache_miss"):
        
        mock_ai.analyze_text.return_value = ai_analysis
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_rag.build_hierarchical_context.return_value = "Context"
        
        await analyze_core.analyze_step(note, user, db_mock, AsyncMock())
        
        # Verify preferences updated
        assert user.adaptive_preferences == {"P0": "critical urgency"}
        db_mock.execute.assert_called() # update(User) call

@pytest.mark.asyncio
async def test_ask_clarification_on_uncertainty():
    """Test that AI returns ask_clarification when 'not sure' is in summary."""
    db_mock = AsyncMock()
    note = MagicMock(spec=Note)
    note.transcription_text = "Vague message."
    note.action_items = []
    
    user = MagicMock(spec=User)
    user.adaptive_preferences = {}
    
    # Summary containing 'not sure'
    ai_analysis = {
        "summary": "I am not sure what the priority is.",
        "mood": "neutral"
    }
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service") as mock_rag, \
         patch("app.core.analyze_core.track_cache_miss"):
        
        mock_ai.analyze_text.return_value = ai_analysis
        mock_ai.generate_embedding.return_value = [0.1]*1536
        
        analysis, _ = await analyze_core.analyze_step(note, user, db_mock, AsyncMock())
        
        # Verify clarification was promoted
        assert "ask_clarification" in analysis
        assert "Clarification Needed:" in note.action_items[0]
