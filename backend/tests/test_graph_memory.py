import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.core.rag_service import rag_service
from app.models import Note, NoteRelation, NoteEmbedding, User, LongTermMemory
import json

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Mock scalars().all() pattern
    mock_res = MagicMock(name="Result")
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalars.return_value.first.return_value = None
    session.execute.return_value = mock_res
    session.__aenter__.return_value = session
    return session

@pytest.mark.asyncio
async def test_generate_relations(mock_db_session):
    """Test that reflection correctly identifies and saves note relations via DeepSeek."""
    user_id = "test_user_relations"
    
    # 1. Setup existing notes for reflection
    n1 = Note(id="n1", transcription_text="Note about Python development")
    n2 = Note(id="n2", transcription_text="Note about database schema change")
    
    mock_res_notes = MagicMock(name="NotesResult")
    mock_res_notes.scalars.return_value.all.return_value = [n1, n2]
    
    mock_res_user = MagicMock(name="UserResult")
    mock_res_user.scalars.return_value.first.return_value = User(id=user_id)
    
    mock_db_session.execute.side_effect = [
        mock_res_notes, # Reflection notes fetch
        mock_res_user   # User object fetch for identity update
    ]
    
    # 2. Mock AI responses (Reflection Summary + Relations)
    mock_ai = AsyncMock()
    # First call: Daily Summary JSON
    # Second call: Relations JSON list
    mock_ai.get_chat_completion.side_effect = [
        json.dumps({
            "summary": "Development summary", 
            "identity_summary": "Identity overview", 
            "importance_score": 7.0
        }, ensure_ascii=False),
        json.dumps([
            {"note1_id": "n1", "note2_id": "n2", "type": "related", "strength": 0.9}
        ], ensure_ascii=False)
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
        assert relations[0].strength == 0.9

@pytest.mark.asyncio
async def test_traversal(mock_db_session):
    """Test graph traversal in RAG: verify that neighbor notes are added to context."""
    user_id = "u1"
    note_id = "seed"
    
    # Setup: Note V1 (Vector Match) is matched first
    v1 = Note(id="v1", title="Vector Note", summary="Vector Summary content")
    # Setup: Note G1 is a graph neighbor of V1
    g1 = Note(id="g1", title="Graph Neighbor", summary="Graph summary content")
    
    # Mock Relation
    rel = NoteRelation(note_id1="v1", note_id2="g1", strength=0.95)
    
    # Mock sequence of DB executions in get_medium_term_context
    # 1. Vector Search (Notes with join NoteEmbedding)
    mock_res_v = MagicMock(name="VectorRes")
    mock_res_v.scalars.return_value.all.return_value = [v1]
    
    # 2. Relation search for neighbors of v1
    mock_res_rel = MagicMock(name="RelationRes")
    mock_res_rel.scalars.return_value.all.return_value = [rel]
    
    # 3. Fetching neighbors (g1) content
    mock_res_nb = MagicMock(name="NeighborRes")
    mock_res_nb.scalars.return_value.all.return_value = [g1]
    
    mock_db_session.execute.side_effect = [mock_res_v, mock_res_rel, mock_res_nb]
    
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("app.core.rag_service.ai_service", mock_ai):
        context_data = await rag_service.get_medium_term_context(user_id, note_id, "test query", mock_db_session)
        
        assert "Vector Note" in context_data["vector"]
        # Verification of the specific "Related note:" prefix requested
        assert "Related note: Graph summary content" in context_data["graph"]

@pytest.mark.asyncio
async def test_full_context_assembly(mock_db_session):
    """Test hierarchical assembly includes graph connections accurately."""
    note = Note(id="n_root", user_id="u1", transcription_text="query")
    
    # Mock all context tiers as empty or basic
    mock_res_empty = MagicMock()
    mock_res_empty.scalars.return_value.all.return_value = []
    
    # Medium Term logic uses 3 calls (vector search, relation search, neighbor fetch)
    # We provide 1 match for each to see them in final prompt
    v = Note(id="v1", title="VMatch", summary="VSum")
    rel = NoteRelation(note_id1="v1", note_id2="g1", strength=0.8)
    g = Note(id="g1", title="GMatch", summary="GSum")
    
    m_res_v = MagicMock(); m_res_v.scalars.return_value.all.return_value = [v]
    m_res_r = MagicMock(); m_res_r.scalars.return_value.all.return_value = [rel]
    m_res_g = MagicMock(); m_res_g.scalars.return_value.all.return_value = [g]

    mock_db_session.execute.side_effect = [
        mock_res_empty, # Short term
        m_res_v,        # Medium term vector
        m_res_r,        # Medium term relation
        m_res_g,        # Medium term neighbor
        mock_res_empty  # Long term
    ]
    
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("app.core.rag_service.ai_service", mock_ai):
        full_context = await rag_service.build_hierarchical_context(note, mock_db_session)
        
        assert "Recent context (Similar notes):" in full_context
        assert "VMatch" in full_context
        assert "Graph connections:" in full_context
        assert "Related note: GSum" in full_context
