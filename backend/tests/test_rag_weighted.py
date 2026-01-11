import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.rag_service import rag_service
from app.models import Note, NoteRelation, NoteEmbedding

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_graph_traversal_weighted():
    # Manual Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    user_id = "u1"
    
    import datetime
    # Mock Vector Search Result
    n1 = Note(id="n1", user_id=user_id, title="Source", created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc))
    n1.importance_score = 5.0
    
    # Mock Neighbors
    n2 = Note(id="n2", user_id=user_id, title="Strong Neighbor")
    
    # Mock Relations
    rel1 = NoteRelation(note_id1="n1", note_id2="n2", strength=0.9, confidence=0.8)
    
    # Mocks
    mock_vector_res = MagicMock()
    mock_vector_res.scalars.return_value.all.return_value = [n1]
    
    mock_graph_res = MagicMock()
    mock_graph_res.scalars.return_value.all.return_value = [rel1] 
    
    mock_dist_res = MagicMock()
    mock_dist_res.all.return_value = [(n2, 0.1)]
    
    mock_db.execute.side_effect = [
        mock_vector_res, # Vector search
        mock_graph_res,  # Graph search
        mock_dist_res    # Neighbor Dist search
    ]
    
    with patch("app.core.rag_service.ai_service.generate_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.1]*1536
        
        try:
            result = await rag_service.get_medium_term_context(user_id, "n_other", "query", mock_db)
            
            # Verify Graph Context string contains n2
            assert "Strong Neighbor" in result["graph"]
            assert "Weak Neighbor" not in result["graph"]
            
        except Exception as e:
            print(f"TEST EXCEPTION: {e}")
            raise
        
        # Verify Graph Context string contains n2
        assert "Strong Neighbor" in result["graph"]
        assert "Weak Neighbor" not in result["graph"]
        
        # Verify SQL filter arg was present (implied by us mocking return of only rel1, but good to check if possible)
        # We can check call args of db.execute[1]
        
        # Check logic: Weighted score sorting happened.
        # Since only 1 result, it sorted trivially.
