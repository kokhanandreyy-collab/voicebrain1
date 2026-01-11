import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from tasks.reflection import _calculate_composite_importance, _process_reflection_async
from app.models import LongTermMemory, User, Note

def test_composite_score_math():
    """Verify that composite score correctly weights different factors."""
    score = _calculate_composite_importance(
        base_score=5.0, # 3.0
        ref_count=5,    # 1.0
        note_count=30,  # 1.0
        has_actions=True, # 1.0
        avg_days=0.0    # 1.0
    )
    assert score == 7.0

@pytest.mark.asyncio
async def test_reflection_composite_save():
    """Test that reflection task calculates and saves the composite score."""
    user_id = "u1"
    
    # Setup Data
    user = User(id=user_id, stable_identity="")
    now = datetime.datetime.now(datetime.timezone.utc)
    n1 = Note(id="n1", title="n1", transcription_text="t1", action_items=["buy"], importance_score=8.0, created_at=now)
    n2 = Note(id="n2", title="n2", transcription_text="t2", action_items=[], importance_score=8.0, created_at=now)
    
    # Setup Result Mocks (Pure MagicMock)
    m_count_notes = MagicMock(name='cnt_notes')
    m_count_notes.scalar.return_value = 2
    
    m_count_rels = MagicMock(name='cnt_rels')
    m_count_rels.scalar.return_value = 0
    
    m_user_res = MagicMock(name='user_res')
    m_user_res.scalars.return_value.first.return_value = user
    
    m_notes_res = MagicMock(name='notes_res')
    m_notes_res.scalars.return_value.all.return_value = [n1, n2]

    # DB Session Mock (Pure MagicMock to avoid Auto-Asyncification)
    db_mock = MagicMock(name='db_session')
    
    async def fake_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "count" in stmt_str and "note" in stmt_str and "noterelation" not in stmt_str:
             return m_count_notes
        if "count" in stmt_str and "noterelation" in stmt_str:
             return m_count_rels
        if "from users" in stmt_str:
             return m_user_res
        if "from notes" in stmt_str:
             return m_notes_res
        return MagicMock()

    db_mock.execute.side_effect = fake_execute
    
    # Handle Async Context Manager manually
    async def async_enter(*args, **kwargs):
        return db_mock
    async def async_exit(*args, **kwargs):
        pass
    
    db_mock.__aenter__.side_effect = async_enter
    db_mock.__aexit__.side_effect = async_exit
    
    async def fake_commit():
        pass
    db_mock.commit.side_effect = fake_commit
    
    # We must patch AsyncSessionLocal to return our Manual DB Mock
    # AsyncSessionLocal() -> returns db_mock
    
    # AI Service Mock
    mock_ai = AsyncMock()
    mock_ai.clean_json_response = MagicMock(side_effect=lambda x: x) 
    
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "Facts", "importance_score": 5.0}', 
        '{"stable_identity": "ID", "volatile_preferences": {}}', 
        '[{"note1_id": "n1", "note2_id": "n2", "relation_type": "rel", "strength": 1.0}]' 
    ]
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor") as mock_monitor:
         
        await _process_reflection_async(user_id)
        
        # Check added memory
        added_objs = [call.args[0] for call in db_mock.add.call_args_list if isinstance(call.args[0], LongTermMemory)]
        assert len(added_objs) == 1
        ltm = added_objs[0]
        
        # Verify score
        assert ltm.importance_score > 5.0
