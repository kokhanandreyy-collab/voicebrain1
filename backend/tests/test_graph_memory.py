import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.reflection import _process_reflection_async
from app.models import Note, NoteRelation

@pytest.mark.asyncio
async def test_reflection_graph_extraction():
    """Test that reflection extracts and saves note relations."""
    user_id = "test-user-123"
    
    # Mock Database
    db_mock = AsyncMock()
    
    # Mock Notes
    mock_notes = [
        Note(id="note-1", transcription_text="I started a new project today."),
        Note(id="note-2", transcription_text="I'm using Python for my new project.")
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_notes
    db_mock.execute.return_value = mock_result
    
    # Mock AI Service
    mock_ai = AsyncMock()
    # Summary response
    mock_ai.get_chat_completion.side_effect = [
        '{"summary": "User started a Python project.", "importance_score": 8.0}', # Summary
        '[{"note1_id": "note-1", "note2_id": "note-2", "relation_type": "related", "strength": 0.9}]' # Relations
    ]
    mock_ai.clean_json_response.side_effect = lambda x: x
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai):
        
        await _process_reflection_async(user_id)
        
        # Verify db.add_all was called for relations
        # We check calls to add/add_all
        # The code adds LongTermMemory then NoteRelation list
        assert db_mock.add.call_count >= 1 # LongTermMemory
        assert db_mock.add_all.call_count >= 1 # NoteRelations
        
        # Check relation content
        rels_saved = db_mock.add_all.call_args[0][0]
        assert len(rels_saved) == 1
        assert rels_saved[0].note_id1 == "note-1"
        assert rels_saved[0].note_id2 == "note-2"
        assert rels_saved[0].relation_type == "related"

    db_mock.commit.assert_called_once()
