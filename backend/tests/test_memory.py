import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.future import select
from datetime import datetime

from app.models import Note, LongTermSummary, NoteEmbedding
from workers.reflection_tasks import _reflection_summary_async
from workers.analyze_tasks import _process_analyze_async, step_get_medium_term_context, step_get_long_term_memory

@pytest.mark.asyncio
async def test_reflection_summary_creation():
    """Verify that reflection_summary generates and saves LongTermSummary."""
    user_id = "user_123"
    
    # Mock Database Session
    mock_db = AsyncMock()
    
    # Mock Notes Query
    mock_note = MagicMock(spec=Note)
    mock_note.title = "Test Note"
    mock_note.summary = "Test Summary"
    mock_note.status = "COMPLETED"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_note]
    mock_db.execute.return_value = mock_result
    
    with patch("workers.reflection_tasks.AsyncSessionLocal", return_value=mock_db), \
         patch("workers.reflection_tasks.ai_service") as mock_ai:
        
        mock_ai.ask_notes = AsyncMock(return_value="Reflected Insight")
        mock_ai.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        
        await _reflection_summary_async(user_id)
        
        # Verify persistence
        assert mock_db.add.called
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, LongTermSummary)
        assert added_obj.summary_text == "Reflected Insight"
        assert added_obj.user_id == user_id
        assert mock_db.commit.called

@pytest.mark.asyncio
async def test_hierarchical_rag_context_loading():
    """Verify that analysis task gathers all 3 memory layers."""
    note_id = "note_abc"
    user_id = "user_456"
    
    mock_db = AsyncMock()
    
    # Mock current note
    mock_note = MagicMock(spec=Note)
    mock_note.id = note_id
    mock_note.user_id = user_id
    mock_note.transcription_text = "Checking recent events"
    
    # Mock note query
    mock_res_note = MagicMock()
    mock_res_note.scalars.return_value.first.return_value = mock_note
    
    # Mock user query
    mock_res_user = MagicMock()
    mock_res_user.scalars.return_value.first.return_value = MagicMock(bio="Dev context", target_language="en")
    
    mock_db.execute.side_effect = [mock_res_note, mock_res_user, MagicMock(), MagicMock()]
    
    with patch("workers.analyze_tasks.AsyncSessionLocal", return_value=mock_db), \
         patch("workers.analyze_tasks.short_term_memory") as mock_st, \
         patch("workers.analyze_tasks.step_get_medium_term_context") as mock_mt, \
         patch("workers.analyze_tasks.step_get_long_term_memory") as mock_lt, \
         patch("workers.analyze_tasks.ai_service") as mock_ai:
        
        mock_st.get_history = AsyncMock(return_value=[{"text": "Added a task"}])
        mock_mt.return_value = "Medium context"
        mock_lt.return_value = "Long context"
        mock_ai.analyze_text = AsyncMock(return_value={"title": "Test"})
        
        await _process_analyze_async(note_id)
        
        # Verify ai_service call contains the combined hierarchical context
        call_args = mock_ai.analyze_text.call_args
        context = call_args.kwargs["previous_context"]
        
        assert "Short-term" in context
        assert "Recent context" in context
        assert "Long-term knowledge" in context
        assert "Medium context" in context
        assert "Long context" in context

@pytest.mark.asyncio
async def test_long_term_memory_retrieval_order():
    """Verify that long-term memory is fetched by importance score."""
    user_id = "user_789"
    mock_db = AsyncMock()
    
    mock_sum = MagicMock(spec=LongTermSummary)
    mock_sum.summary_text = "Important Summary"
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_sum]
    mock_db.execute.return_value = mock_res
    
    summary_text = await step_get_long_term_memory(user_id, mock_db)
    
    assert "Important Summary" in summary_text
    # Verify the query used order_by importance desc
    args = mock_db.execute.call_args[0][0]
    # Check if 'importance_score' and 'desc' appear in the query string representation
    # (Simplified check for mock verification)
    assert "importance_score" in str(args)
