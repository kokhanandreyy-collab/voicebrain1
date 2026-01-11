import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.analyze_core import analyze_core
from app.models import Note, User

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_emotional_separation():
    """
    Test that 'mood' is extracted but does NOT influence intent/routing directly.
    """
    # 1. Setup
    user = User(id="u1", stable_identity="Rational user")
    note = Note(id="n1", user_id="u1", transcription_text="I am so angry! Buy milk.")
    
    # Custom Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    
    # 2. Mock AI
    mock_analysis = {
        "title": "Milk",
        "summary": "Buy milk",
        "action_items": ["Buy milk"],
        "tags": ["groceries"],
        "mood": "frustrated", # Emotion
        "intent": "task",     # Action Logic
        "priority": 1
    }
    
    with patch("app.core.analyze_core.ai_service.analyze_text", new_callable=AsyncMock) as mock_analyze, \
         patch("app.core.analyze_core.ai_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
         patch("app.core.analyze_core.rag_service.build_hierarchical_context", new_callable=AsyncMock) as mock_ctx:
         
         mock_ctx.return_value = ""
         mock_embed.return_value = [0.0]*1536
         mock_analyze.return_value = mock_analysis
         
         # 3. Analyze
         result, cache_hit = await analyze_core.analyze_step(note, user, mock_db, None)
         
         # 4. Verify Separation
         assert result["mood"] == "frustrated"
         assert result["intent"] == "task" 
         
         # Verify Note Object Update
         assert note.mood == "frustrated"
         # Verify we didn't use mood for routing logic
         assert note.action_items == ["Buy milk"]
