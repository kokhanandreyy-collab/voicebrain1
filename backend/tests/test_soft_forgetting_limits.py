import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from tasks.cleanup_memory import run_cleanup
from app.models import LongTermMemory
from app.core.rag_service import rag_service

@pytest.mark.asyncio
async def test_hard_delete_strictly_time_based():
    """Verify that hard delete is only for records > 365 days."""
    db_mock = AsyncMock()
    
    # We want to check the WHERE clause of the delete statement
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.cleanup_memory.ai_service", AsyncMock()):
        
        await run_cleanup()
        
        # Check call arguments of first execute (which is hard delete)
        delete_stmt = db_mock.execute.call_args_list[0].args[0]
        # It's a SQLAlchemy delete object. We can check its 'whereclamp' (where criteria)
        # But easier to check it just doesn't filter by importance score anymore.
        stmt_str = str(delete_stmt.compile())
        assert "importance_score" not in stmt_str.lower()
        assert "created_at" in stmt_str.lower()

@pytest.mark.asyncio
async def test_rag_filters_archived():
    """Verify RAG retrieval excludes archived records."""
    db_mock = AsyncMock()
    user_id = "u1"
    
    # Mock result containing one archived and one active
    m_active = LongTermMemory(id="active", summary_text="I am active", is_archived=False)
    m_archived = LongTermMemory(id="archived", summary_text="I am archived", is_archived=True)
    
    res = MagicMock()
    res.scalars.return_value.all.return_value = [m_active] # RAG should only get active
    db_mock.execute.return_value = res
    
    with patch("app.core.rag_service.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        
        context = await rag_service.get_long_term_memory(user_id, db_mock)
        
        # Check the actual query executed
        query = db_mock.execute.call_args[0][0]
        query_str = str(query.compile())
        assert "is_archived = false" in query_str.lower() or "is_archived = :is_archived_1" in query_str.lower()
        
        assert "I am active" in context
        assert "I am archived" not in context
