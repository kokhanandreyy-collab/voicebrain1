import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.analyze_core import analyze_core
from app.models import Note, User

@pytest.mark.asyncio
async def test_adaptive_memory_detection():
    """Test that DeepSeek uncertainty triggers ask_clarification."""
    note = Note(id="n1", transcription_text="Set priority high for this task", user_id="u1")
    user = User(id="u1", adaptive_preferences={})
    db = AsyncMock()
    memory_service = AsyncMock()
    
    # Mock AI response with uncertainty in summary
    mock_analysis = {
        "title": "Task",
        "summary": "User wants to set high priority. I am not sure what high priority means here (P0 or P1?). Clarify please.",
        "intent": "todo",
        "priority": 1
    }
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="context"), \
         patch("app.core.analyze_core.CachedAnalysis"):
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = mock_analysis
        
        # Execute
        analysis, cache_hit = await analyze_core.analyze_step(note, user, db, memory_service)
        
        # Verify ask_clarification was promoted to action_items
        assert any("Clarification Needed:" in str(item) for item in note.action_items)
        assert "ask_clarification" in analysis

@pytest.mark.asyncio
async def test_adaptive_memory_saving():
    """Test that adaptive_preferences are updated from AI analysis."""
    note = Note(id="n1", transcription_text="P0 means Critical", user_id="u1")
    user = User(id="u1", adaptive_preferences={"old": "val"})
    db = AsyncMock()
    memory_service = AsyncMock()
    
    # Mock AI detecting a preference update
    mock_analysis = {
        "title": "Preference Update",
        "summary": "User defined P0",
        "adaptive_update": {"priority_p0": "Critical"}
    }
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="context"):
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = mock_analysis
        
        # Execute
        await analyze_core.analyze_step(note, user, db, memory_service)
        
        # Verify preferences updated
        assert user.adaptive_preferences["priority_p0"] == "Critical"
        assert user.adaptive_preferences["old"] == "val"
        db.execute.assert_called() # Should call update(User)

@pytest.mark.asyncio
async def test_adaptive_memory_prompt_injection():
    """Test that adaptive_preferences are injected into the AI context."""
    note = Note(id="n1", transcription_text="Test", user_id="u1")
    user = User(id="u1", adaptive_preferences={"p0": "Critical"})
    db = AsyncMock()
    memory_service = AsyncMock()
    
    with patch("app.core.analyze_core.ai_service") as mock_ai, \
         patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="context"):
        
        mock_ai.generate_embedding.return_value = [0.1]*1536
        mock_ai.analyze_text.return_value = {}
        
        await analyze_core.analyze_step(note, user, db, memory_service)
        
        # Verify ai_service.analyze_text was called with user_context containing preferences
        args, kwargs = mock_ai.analyze_text.call_args
        user_context = kwargs.get("user_context", "")
        assert '"p0": "Critical"' in user_context
        assert "Adaptive preferences:" in user_context
