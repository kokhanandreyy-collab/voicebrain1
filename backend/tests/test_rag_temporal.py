import pytest
import math
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.rag_service import RagService
from app.models import LongTermMemory, Note

@pytest.mark.asyncio
async def test_temporal_weighting_logic():
    """Test that newer items are prioritized over older ones despite lower raw importance."""
    rag = RagService()
    user_id = "user123"
    db_mock = AsyncMock()
    
    # Mock settings.RAG_TEMPORAL_DECAY_DAYS = 30
    with patch("app.core.rag_service.settings") as mock_settings:
        mock_settings.RAG_TEMPORAL_DECAY_DAYS = 30
        
        # 1. Setup mock memories
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Old but very important (Importance 10, 60 days old)
        old_mem = MagicMock(spec=LongTermMemory)
        old_mem.summary_text = "Old important memory"
        old_mem.importance_score = 10.0
        old_mem.created_at = now - datetime.timedelta(days=60)
        
        # New and moderately important (Importance 5, 1 day old)
        new_mem = MagicMock(spec=LongTermMemory)
        new_mem.summary_text = "New moderate memory"
        new_mem.importance_score = 5.0
        new_mem.created_at = now - datetime.timedelta(days=1)
        
        # Mock DB results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_mem, new_mem]
        db_mock.execute.return_value = mock_result
        
        # Call without query_text (general summary retrieval)
        result_text = await rag.get_long_term_memory(user_id, db_mock)
        
        # New memory should be first because:
        # Score(New) = 5 * exp(-1/30) ~= 4.8
        # Score(Old) = 10 * exp(-60/30) ~= 1.35
        
        assert "New moderate memory" in result_text
        # Verify order in the returned string (if we can infer it)
        lines = result_text.split("\n")
        assert "New moderate memory" in lines[0]
        assert "Old important memory" in lines[1]

@pytest.mark.asyncio
async def test_temporal_weighting_hybrid():
    """Test that temporal weighting applies in hybrid vector search re-ranking."""
    rag = RagService()
    db_mock = AsyncMock()
    
    with patch("app.core.rag_service.settings") as mock_settings, \
         patch("app.core.rag_service.ai_service") as mock_ai:
        
        mock_settings.RAG_TEMPORAL_DECAY_DAYS = 30
        mock_ai.generate_embedding.return_value = [0.1] * 1536
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Old (importance 10, 90 days old)
        old_mem = MagicMock(spec=LongTermMemory)
        old_mem.summary_text = "Ancient Wisdom"
        old_mem.importance_score = 10.0
        old_mem.created_at = now - datetime.timedelta(days=90)
        
        # New (importance 3, today)
        new_mem = MagicMock(spec=LongTermMemory)
        new_mem.summary_text = "Fresh News"
        new_mem.importance_score = 3.0
        new_mem.created_at = now
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_mem, new_mem]
        db_mock.execute.return_value = mock_result
        
        result_text = await rag.get_long_term_memory("user", db_mock, query_text="help")
        
        # Score Fresh = 3 * exp(0) = 3
        # Score Ancient = 10 * exp(-3) ~= 10 * 0.05 = 0.5
        assert "Fresh News" in result_text.split("\n")[0]
