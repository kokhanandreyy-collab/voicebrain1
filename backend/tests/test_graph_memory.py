import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.core.rag_service import rag_service
from app.models import Note, NoteRelation, NoteEmbedding, User
import json

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Mock scalars().all() pattern
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_res
    return session

@pytest.mark.asyncio
async def test_generate_relations(mock_db_session):
    """Test that reflection correctly identifies and saves note relations."""
    user_id = "u1"
    
    # Query for notes
    mock_res_notes = MagicMock(name="NotesResult")
    n1 = Note(id="n1", transcription_text="First note text")
    n2 = Note(id="n2", transcription_text="Second note text")
    mock_res_notes.scalars.return_value.all.return_value = [n1, n2]
    
    # Query for user 
    mock_res_user = MagicMock(name="UserResult")
    mock_res_user.scalars.return_value.first.return_value = User(id=user_id)
    
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_res_notes,
        mock_res_user
    ])
    mock_db_session.__aenter__.return_value = mock_db_session
    
    # Mock AI response with relations
    mock_ai = AsyncMock()
    # First call: Summary
    # Second call: Relations
    mock_ai.get_chat_completion.side_effect = [
        json.dumps({"summary": "Summary", "identity_summary": "Identity", "importance_score": 5.0}),
        json.dumps([{"note1_id": "n1", "note2_id": "n2", "type": "caused", "strength": 0.8}])
    ]
    mock_ai.get_embedding.return_value = [0.1] * 1536
    mock_ai.clean_json_response = lambda x: x
    
    with patch("workers.reflection_tasks.ai_service", mock_ai), \
         patch("workers.reflection_tasks.AsyncSessionLocal", return_value=mock_db_session):
        await _process_reflection_async(user_id)
        
        # Verify db.add was called for NoteRelation
        added_objects = [call.args[0] for call in mock_db_session.add.call_args_list]
        relations = [obj for obj in added_objects if isinstance(obj, NoteRelation)]
        
        assert len(relations) == 1
        assert relations[0].note_id1 == "n1"
        assert relations[0].note_id2 == "n2"
        assert relations[0].relation_type == "caused"
        assert relations[0].strength == 0.8

@pytest.mark.asyncio
async def test_graph_traversal(mock_db_session):
    """Test that RAG retrieval pulls in neighbor notes via relations."""
    user_id = "u1"
    note_id = "n1"
    
    # 1. Main Vector Match
    n1 = Note(id="n1", title="Vector Note", summary="Summary 1")
    # 2. Graph Neighbor
    n2 = Note(id="n2", title="Graph Neighbor", summary="Summary 2")
    
    # NoteRelation between them
    rel = NoteRelation(note_id1="n1", note_id2="n2", strength=0.9)
    
    # Setup execute results
    # 1. Vector Search Note find
    mock_res_vector = MagicMock()
    mock_res_vector.scalars.return_value.all.return_value = [n1]
    
    # 2. Relation search
    mock_res_rel = MagicMock()
    mock_res_rel.scalars.return_value.all.return_value = [rel]
    
    # 3. Fetch Neighbor Note
    mock_res_nb = MagicMock()
    mock_res_nb.scalars.return_value.all.return_value = [n2]
    
    mock_db_session.execute.side_effect = [
        mock_res_vector,
        mock_res_rel,
        mock_res_nb
    ]
    
    # Mock embedding
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("app.core.rag_service.ai_service", mock_ai):
        context = await rag_service.get_medium_term_context(user_id, note_id, "query", mock_db_session)
        
        assert "Vector Note" in context
        assert "Graph Neighbor" in context
        assert "Summary 2" in context
