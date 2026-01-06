import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.models import Note, NoteRelation
import json

@pytest.mark.asyncio
async def test_graph_relation_extraction():
    """Test that reflection task extracts graph-like relations between notes."""
    user_id = "user123"
    db_mock = AsyncMock()
    
    # Mock notes
    n1 = MagicMock(spec=Note)
    n1.id = "note-uuid-1"
    n1.transcription_text = "Planning the vacation to Iceland."
    n1.created_at = "2024-01-01"
    
    n2 = MagicMock(spec=Note)
    n2.id = "note-uuid-2"
    n2.transcription_text = "I need to buy warm boots for Iceland."
    n2.created_at = "2024-01-02"

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [n1, n2]
    db_mock.execute.return_value = mock_res
    
    # Mock AI Responses
    # 1. Summary response
    summary_resp = json.dumps({
        "summary": "Iceland planning",
        "identity_summary": "Traveler",
        "importance_score": 7.0
    })
    
    # 2. Relations response
    rel_resp = json.dumps([
        {"note1_id": "note-uuid-1", "note2_id": "note-uuid-2", "type": "caused", "strength": 0.9}
    ])
    
    with patch("workers.reflection_tasks.ai_service") as mock_ai, \
         patch("workers.reflection_tasks.AsyncSessionLocal", return_value=db_mock), \
         patch("workers.reflection_tasks.track_cache_miss"):
        
        # Sequentially return summary then relations
        mock_ai.get_chat_completion.side_effect = [summary_resp, rel_resp]
        mock_ai.clean_json_response.side_effect = [summary_resp, rel_resp]
        mock_ai.get_embedding.return_value = [0.1] * 1536
        
        await _process_reflection_async(user_id)
        
        # Verify db.add_all was called for NoteRelation
        # We need to find the add_all call that contains NoteRelation objects
        found_relations = False
        for call in db_mock.add_all.call_args_list:
            items = call.args[0]
            if items and isinstance(items[0], NoteRelation):
                found_relations = True
                assert items[0].note_id1 == "note-uuid-1"
                assert items[0].note_id2 == "note-uuid-2"
                assert items[0].relation_type == "caused"
        
        assert found_relations
        db_mock.commit.assert_called_once()
