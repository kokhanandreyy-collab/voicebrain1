import pytest
import datetime
import math
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.rag_service import rag_service
from app.models import Note, LongTermMemory

@pytest.mark.asyncio
async def test_temporal_weighting_calculation():
    """Test the decay math directly."""
    # Importance 10, Created now
    now = datetime.datetime.now(datetime.timezone.utc)
    score_now = rag_service._calculate_temporal_score(10.0, now)
    assert math.isclose(score_now, 10.0, rel_tol=1e-5)
    
    # Importance 10, Created 30 days ago (should be 10 * e^-1 ~ 3.67)
    old_date = now - datetime.timedelta(days=30)
    score_old = rag_service._calculate_temporal_score(10.0, old_date)
    assert score_old < 4.0
    assert score_old > 3.6

@pytest.mark.asyncio
async def test_rag_prioritizes_fresh_notes():
    """Test that RAG retrieval prioritizes fresher notes over older high-importance ones if the decay is significant."""
    db_mock = AsyncMock()
    user_id = "u1"
    
    now = datetime.datetime.now(datetime.timezone.utc)
    # n1: 60 days old, score 10
    # n2: 1 day old, score 6
    n1 = Note(id="old", title="Old High", importance_score=10.0, created_at=now - datetime.timedelta(days=60))
    n2 = Note(id="new", title="New Med", importance_score=6.0, created_at=now - datetime.timedelta(days=1))
    
    # Mock vector results fetching both
    v_res = MagicMock()
    v_res.scalars.return_value.all.return_value = [n1, n2]
    db_mock.execute.return_value = v_res
    
    with patch("app.core.rag_service.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        
        context = await rag_service.get_medium_term_context(user_id, "id-current", "query", db_mock)
        
        # New Med (6 * e^-0.03 ~ 5.8) should be higher than Old High (10 * e^-2 ~ 1.35)
        # So New Med should appear first in the formatted list if the re-ranking worked.
        # Check that 'New Med' is before 'Old High' in the string
        vector_str = context["vector"]
        assert vector_str.index("New Med") < vector_str.index("Old High")

@pytest.mark.asyncio
async def test_long_term_temporal_weighting():
    """Test re-ranking in long-term memory."""
    db_mock = AsyncMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    m1 = LongTermMemory(summary_text="Old Knowledge", importance_score=10.0, created_at=now - datetime.timedelta(days=100))
    m2 = LongTermMemory(summary_text="Recent News", importance_score=5.0, created_at=now - datetime.timedelta(days=2))
    
    res = MagicMock()
    res.scalars.return_value.all.return_value = [m1, m2]
    db_mock.execute.return_value = res
    
    context = await rag_service.get_long_term_memory("u1", db_mock)
    
    # Recent News should be higher score
    # 5 * e^(-2/30) vs 10 * e^(-100/30)
    # 5 * 0.93 = 4.65
    # 10 * 0.035 = 0.35
    assert context.index("Recent News") < context.index("Old Knowledge")
