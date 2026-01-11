import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from tasks.reflection import _calculate_composite_importance, _process_reflection_async
from app.models import LongTermMemory, User, Note

def test_composite_score_math():
    """Verify that composite score correctly weights different factors."""
    # base_score * 0.6 + refs * 0.1 + rec * 0.1 + act * 0.1 + time * 0.1
    # Normalized: 
    # refs: 5 refs -> 10 pts
    # rec: 30 notes -> 10 pts
    # act: True -> 10 pts
    # time: 0 days ago -> 10 pts
    
    score = _calculate_composite_importance(
        base_score=5.0, # 5 * 0.6 = 3.0
        ref_count=5,    # 10 * 0.1 = 1.0
        note_count=30,  # 10 * 0.1 = 1.0
        has_actions=True, # 10 * 0.1 = 1.0
        avg_days=0.0    # 10 * 0.1 = 1.0
    )
    # Total: 3 + 1 + 1 + 1 + 1 = 7.0
    assert score == 7.0

@pytest.mark.asyncio
async def test_reflection_composite_save():
    """Test that reflection task calculates and saves the composite score."""
    user_id = "u1"
    db_mock = AsyncMock()
    
    user = User(id=user_id, stable_identity="")
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = user
    
    # 3 notes, one with action items
    n1 = Note(id="n1", title="n1", transcription_text="t1", action_items=["buy"], importance_score=8.0)
    n2 = Note(id="n2", title="n2", transcription_text="t2", action_items=[], importance_score=8.0)
    notes_res = MagicMock()
    notes_res.scalars.return_value.all.return_value = [n1, n2]
    
    db_mock.execute.side_effect = [
        MagicMock(scalar=lambda: 2), # nodes
        MagicMock(scalar=lambda: 0), # rels
        user_res,
        notes_res
    ]
    
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "Facts", "importance_score": 5.0}', # Step 1: Base Score 5.0
        '{"stable_identity": "ID", "volatile_preferences": {}}', # Step 2
        '[{"note1_id": "n1", "note2_id": "n2", "relation_type": "rel", "strength": 1.0}]' # Step 3: 1 Relation
    ]
    mock_ai.clean_json_response.side_effect = lambda x: x
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai):
        
        await _process_reflection_async(user_id)
        
        # Check added memory
        added_objs = [call.args[0] for call in db_mock.add.call_args_list if isinstance(call.args[0], LongTermMemory)]
        assert len(added_objs) == 1
        ltm = added_objs[0]
        
        # Base: 5.0 * 0.6 = 3.0
        # Refs: 1 rel * 2 = 2 pts * 0.1 = 0.2
        # Recurrence: 2 notes / 3 = 0.66 pts * 0.1 = 0.066
        # Actions: True = 10 pts * 0.1 = 1.0
        # Time: ~10 pts (recent) * 0.1 = 1.0
        # Expected: ~5.26
        assert ltm.importance_score > 5.0
        assert ltm.importance_score < 6.0
