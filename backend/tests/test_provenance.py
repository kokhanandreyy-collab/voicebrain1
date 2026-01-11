import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.reflection import _process_reflection_async
from app.core.rag_service import rag_service
from app.models import LongTermMemory, NoteRelation

@pytest.mark.asyncio
async def test_reflection_provenance():
    """Test that reflection saves confidence and source."""
    user_id = "pro_user"
    
    # DB Mock
    db_mock = AsyncMock()
    
    # Mocks for results
    m_user_res = MagicMock()
    m_user_res.scalars.return_value.first.return_value = MagicMock(id=user_id)
    
    m_notes_res = MagicMock()
    import datetime
    # Fix: Provide created_at to avoid NoneType error in reflection logic
    n1 = MagicMock(id="n1", transcription_text="t", action_items=[], importance_score=8, created_at=datetime.datetime.now(datetime.timezone.utc))
    m_notes_res.scalars.return_value.all.return_value = [n1]
    
    m_count = MagicMock()
    m_count.scalar.return_value = 0

    def execute_side_effect(stmt, *args, **kwargs):
        s = str(stmt).lower()
        if "from users" in s: return m_user_res
        if "from notes" in s: return m_notes_res
        if "count" in s: return m_count
        return MagicMock()
    
    db_mock.execute.side_effect = execute_side_effect
    
    # Async context manager
    db_mock.__aenter__.return_value = db_mock
    db_mock.__aexit__.return_value = None
    
    # Fake commit
    db_mock.commit.side_effect = lambda: None

    # AI Mock
    mock_ai = AsyncMock()
    mock_ai.clean_json_response = MagicMock(side_effect=lambda x: x)
    
    # Sequence of AI responses: 
    # 1. Facts (with confidence)
    # 2. Patterns
    # 3. Relations (with confidence)
    
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5, "confidence": 0.9, "source": "fact"}', # Step 1
        '{"stable_identity": "ID", "volatile_preferences": {}}', # Step 2
        '[{"note1_id": "n1", "note2_id": "n2", "relation_type": "rel", "strength": 1.0, "confidence": 0.8, "source": "inferred"}]' # Step 3
    ]
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor"):
         
        await _process_reflection_async(user_id)
        
        # Verify LongTermMemory save
        ltm_calls = [c[0][0] for c in db_mock.add.call_args_list if isinstance(c[0][0], LongTermMemory)]
        assert len(ltm_calls) == 1
        assert ltm_calls[0].confidence == 0.9
        assert ltm_calls[0].source == "fact"
        
        # Verify NoteRelation save
        rel_calls = [c[0][0] for c in db_mock.add.call_args_list if isinstance(c[0][0], NoteRelation)]
        assert len(rel_calls) == 1
        assert rel_calls[0].confidence == 0.8
        assert rel_calls[0].source == "inferred"

@pytest.mark.asyncio
async def test_rag_confidence_filter():
    """Test that RAG filters low confidence memories."""
    db_mock = AsyncMock()
    
    # Mock return values for get_long_term_memory EXECUTE
    # We want to verify the QUERY contains the filter. 
    # It's hard to check the exact SQL string on a mock, but we can check the WHERE clause construction if possible,
    # OR we can just check that high confidence items are returned if we mock the DB to behave "correctly" (too hard).
    # Instead, let's verify parameters passed to execute.
    
    await rag_service.get_long_term_memory("u1", db_mock)
    
    # Inspect the call to db.execute
    # args[0] is the statement.
    call_args = db_mock.execute.call_args
    stmt = call_args[0][0]
    
    # In SQLAlchemy 1.4/2.0, stmt is an object. usage logging typically shows the compiled SQL.
    # checking string representation often reveals the WHERE clause.
    sql = str(stmt)
    assert "long_term_memories.confidence > :confidence_1" in sql or "confidence >" in sql
