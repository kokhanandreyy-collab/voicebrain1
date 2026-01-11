import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import NoteRelation
from tasks.reflection import _process_reflection_async

@pytest.mark.asyncio
async def test_graph_limit_logic():
    """Test max degree check and TTL cleanup."""
    user_id = "u_graph"
    
    # DB Mock
    db_mock = AsyncMock()
    
    # Mocking counts:
    # Scenario: n1 has 10 relations (should be skipped), n2 has 2 (ok)
    # The logic checks c1 and c2 separately inside the loop.
    
    # We'll use a side_effect for execute to return different counts based on query
    m_count_high = MagicMock()
    m_count_high.scalar.return_value = 10
    
    m_count_low = MagicMock()
    m_count_low.scalar.return_value = 2
    
    m_user_res = MagicMock()
    # Need to return valid user
    m_user_res.scalars.return_value.first.return_value = MagicMock(id=user_id, stable_identity="")
    
    m_notes_res = MagicMock()
    # Need valid notes
    import datetime
    n1 = MagicMock(id="n1", transcription_text="t", action_items=[], importance_score=8, created_at=datetime.datetime.now(datetime.timezone.utc))
    n2 = MagicMock(id="n2", transcription_text="t", action_items=[], importance_score=8, created_at=datetime.datetime.now(datetime.timezone.utc))
    m_notes_res.scalars.return_value.all.return_value = [n1, n2]

    # Side effect
    def execute_side_effect(stmt, *args, **kwargs):
        s = str(stmt).lower()
        if "delete" in s: return MagicMock() # Cleanup
        if "from users" in s: return m_user_res
        if "from notes" in s: return m_notes_res
        
        # Max Degree Counts
        if "count" in s and "note_relations" in s:
            # Check params or construction.
            # In code: where((NoteRelation.note_id1 == n1) ...)
            # We can't easily parse SQL params from compiled objects in mocks easily.
            # Let's pivot: Return high count for 1st call (n1), low for 2nd (n2)
             pass
        return MagicMock()

    # To precisely test "per-node" count, we rely on the order of calls inside the loop.
    # relation: n1 -> n2.
    # Logic: check n1 count -> check n2 count.
    # If n1 count >= 10, skip.
    
    # Let's mock side_effect to return 10 then 2.
    # BUT, there are other count calls (total_notes, total_rels) at start.
    # start: count(Note), count(NoteRelation) -> monitor
    # loop: count(n1), count(n2)
    
    # Sequence:
    # 1. Total Notes (monitor) -> 100
    # 2. Total Rels (monitor) -> 100
    # 3. User
    # 4. Notes
    # ... AI Steps ...
    # 5. Delete (TTL)
    # 6. Count n1
    # 7. Count n2 (if n1 < 10)
    
    ex_results = [
        MagicMock(scalar=lambda: 100), # Total Notes
        MagicMock(scalar=lambda: 100), # Total Rels
        m_user_res, # User
        m_notes_res, # Notes
        MagicMock(), # Delete result
        MagicMock(scalar=lambda: 10), # Count n1=10 -> SKIP
        # No more calls expected for this relation
    ]
    
    itr = iter(ex_results)
    def se(stmt):
        return next(itr)
        
    db_mock.execute.side_effect = se
    db_mock.__aenter__.return_value = db_mock
    db_mock.__aexit__.return_value = None
    
    # AI Mock
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.side_effect = [
        '{}', # Step 1
        '{}', # Step 2
        '[{"note1_id": "n1", "note2_id": "n2", "relation_type": "rel", "strength": 1.0}]' # Step 3
    ]
    mock_ai.clean_json_response = MagicMock(side_effect=lambda x: x)
    mock_ai.generate_embedding.return_value = [0.1]*1536

    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor"):
         
        await _process_reflection_async(user_id)
        
        # Verify NO relation added
        added = [c[0][0] for c in db_mock.add.call_args_list if isinstance(c[0][0], NoteRelation)]
        assert len(added) == 0
