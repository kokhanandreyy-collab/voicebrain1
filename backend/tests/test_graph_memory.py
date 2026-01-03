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
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_res
    session.__aenter__.return_value = session
    return session

@pytest.mark.asyncio
async def test_traversal(mock_db_session):
    """Test graph traversal specifically: mock cosine + relations -> check context."""
    user_id = "u1"
    note_id = "n1"
    
    # 1. Main Vector Match
    v_note = Note(id="v1", title="Vector Note", summary="Vector Summary")
    # 2. Graph Neighbor
    g_note = Note(id="g1", title="Graph Note", summary="Graph Summary")
    
    # Relation
    rel = NoteRelation(note_id1="v1", note_id2="g1", strength=0.9)
    
    # Setup execute results
    # 1. Vector Search
    mock_res_v = MagicMock()
    mock_res_v.scalars.return_value.all.return_value = [v_note]
    # 2. Relation search
    mock_res_rel = MagicMock()
    mock_res_rel.scalars.return_value.all.return_value = [rel]
    # 3. Neighbor Notes fetch
    mock_res_g = MagicMock()
    mock_res_g.scalars.return_value.all.return_value = [g_note]
    
    mock_db_session.execute.side_effect = [mock_res_v, mock_res_rel, mock_res_g]
    
    # Mock AI
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("app.core.rag_service.ai_service", mock_ai):
        res = await rag_service.get_medium_term_context(user_id, note_id, "test", mock_db_session)
        assert "Vector Note" in res["vector"]
        assert "Related note: Graph Summary" in res["graph"]

@pytest.mark.asyncio
async def test_full_graph_search(mock_db_session):
    """Test the full context assembly in build_hierarchical_context including graph."""
    note = Note(id="root", user_id="u1", transcription_text="query")
    
    # Mock Short Term (10 notes)
    mock_res_st = MagicMock()
    mock_res_st.scalars.return_value.all.return_value = []
    
    # Mock Medium Term parts (Vector + Graph)
    # get_medium_term_context: Vector search
    mock_res_v = MagicMock()
    mock_res_v.scalars.return_value.all.return_value = [Note(id="v1", title="VMatch", summary="VSum")]
    # get_medium_term_context: Relation search
    mock_res_rel = MagicMock()
    mock_res_rel.scalars.return_value.all.return_value = [NoteRelation(note_id1="v1", note_id2="g1", strength=0.9)]
    # get_medium_term_context: Neighbor fetch
    mock_res_g = MagicMock()
    mock_res_g.scalars.return_value.all.return_value = [Note(id="g1", title="GMatch", summary="GSum")]
    
    # Mock Long Term
    mock_res_lt = MagicMock()
    mock_res_lt.scalars.return_value.all.return_value = []
    
    mock_db_session.execute.side_effect = [
        mock_res_st, # Short term
        mock_res_v,  # Medium term vector
        mock_res_rel, # Medium term relation
        mock_res_g,  # Medium term neighbor
        mock_res_lt  # Long term
    ]
    
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("app.core.rag_service.ai_service", mock_ai):
        full_context = await rag_service.build_hierarchical_context(note, mock_db_session)
        
        assert "Graph connections:" in full_context
        assert "Related note: GSum" in full_context
        assert "Recent context (Similar notes):" in full_context
        assert "VMatch" in full_context
