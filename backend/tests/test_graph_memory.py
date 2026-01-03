import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.models import Note, User, NoteRelation

@pytest.mark.asyncio
async def test_graph_relation_extraction(mock_db_session):
    """Test that relationships are extracted and saved."""
    user_id = "u_graph"
    
    # 1. Mock DB 
    note1 = Note(id="n1", user_id=user_id, transcription_text="I started project A", created_at="2024-01-01")
    note2 = Note(id="n2", user_id=user_id, transcription_text="Project A failed due to lack of time", created_at="2024-01-02")
    
    mock_notes_res = MagicMock()
    mock_notes_res.scalars().all.return_value = [note1, note2]
    
    mock_user = User(id=user_id, identity_summary="Old")
    mock_user_res = MagicMock()
    mock_user_res.scalars().first.return_value = mock_user
    
    mock_db_session.execute.side_effect = [mock_notes_res, mock_user_res]
    
    # 2. Mock AI
    # First call is Summary
    # Second call is Relations
    
    summary_resp = '{"summary": "Sum", "identity_summary": "Id", "importance_score": 5.0}'
    relation_resp = '{"relations": [{"id1": "n1", "id2": "n2", "type": "caused", "strength": 0.9}]}'
    
    with patch("workers.reflection_tasks.ai_service") as mock_ai, \
         patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db_session
         mock_ai.get_chat_completion.side_effect = [summary_resp, relation_resp]
         mock_ai.clean_json_response.side_effect = [summary_resp, relation_resp]
         mock_ai.get_embedding.return_value = [0.0]*1536
         
         await _process_reflection_async(user_id)
         
         # 3. Verify
         # Check that NoteRelation was added
         added_objects = [call.args[0] for call in mock_db_session.add.call_args_list]
         relations = [obj for obj in added_objects if isinstance(obj, NoteRelation)]
         
         assert len(relations) == 1
         rel = relations[0]
         assert rel.note_id1 == "n1"
         assert rel.note_id2 == "n2"
         assert rel.relation_type == "caused"
         assert rel.strength == 0.9
