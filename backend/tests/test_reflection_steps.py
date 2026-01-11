import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.reflection import _process_reflection_async
from app.models import Note, User, LongTermMemory, NoteRelation

@pytest.mark.asyncio
async def test_multi_step_reflection_logic():
    """Test that reflection runs in 3 distinct steps with correct roles."""
    user_id = "u1"
    
    # Setup User
    user = User(id=user_id, stable_identity="", volatile_preferences={})
    
    # Setup Notes
    n1 = Note(id="n1", transcription_text="Met John today.", importance_score=8.5, user_id=user_id)
    
    # Setup DB Result Mocks
    # 1. Count Notes
    res_count_notes = MagicMock()
    res_count_notes.scalar.return_value = 1
    
    # 2. Count Rels
    res_count_rels = MagicMock()
    res_count_rels.scalar.return_value = 0
    
    # 3. User Fetch
    res_user = MagicMock()
    res_user.scalars.return_value.first.return_value = user
    
    # 4. Notes Fetch
    res_notes = MagicMock()
    res_notes.scalars.return_value.all.return_value = [n1]
    
    # DB Session Mock
    db_mock = AsyncMock()
    # Configure execute to return the mocks sequentially
    db_mock.execute.side_effect = [
        res_count_notes,
        res_count_rels,
        res_user,
        res_notes
    ]
    
    # AI Service Mock
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "Met John", "importance_score": 8.0}', # Step 1: Facts
        '{"stable_identity": "Friendly", "volatile_preferences": {"mood": "positive"}}', # Step 2: Patterns
        '[{"note1_id": "n1", "note2_id": "n2", "relation_type": "related", "strength": 0.8}]' # Step 3: Relations
    ]
    mock_ai.clean_json_response.side_effect = lambda x: x
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor") as mock_monitor:
        
        await _process_reflection_async(user_id)
        
        # Verify 3 AI calls
        assert mock_ai.get_chat_completion.call_count == 3
        
        # Verify Step 1: LongTermMemory added
        ltm_added = [call.args[0] for call in db_mock.add.call_args_list if isinstance(call.args[0], LongTermMemory)]
        assert len(ltm_added) == 1
        assert ltm_added[0].summary_text == "Met John"
        
        # Verify Step 2: User updated
        assert user.stable_identity == "Friendly"
        assert user.volatile_preferences["mood"] == "positive"
        
        # Verify Step 3: Relation added
        rel_added = [call.args[0] for call in db_mock.add.call_args_list if isinstance(call.args[0], NoteRelation)]
        assert len(rel_added) == 1
        assert rel_added[0].strength == 0.8
