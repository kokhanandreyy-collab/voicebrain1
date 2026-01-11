import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.reflection import _process_reflection_async
from app.models import Note, NoteRelation, User
from app.core.rag_service import rag_service

@pytest.mark.asyncio
async def test_reflection_graph_importance_limit():
    """Test that reflection only extracts relations for notes with score >= 7."""
    user_id = "u1"
    db_mock = AsyncMock()
    
    # User mock
    user = User(id=user_id, stable_identity="", volatile_preferences={})
    user_res = MagicMock()
    user_res.scalars.return_value.first.return_value = user
    
    # Notes mock: one high importance, one low importance
    n1 = Note(id="n1", transcription_text="High imp", importance_score=8.0, user_id=user_id)
    n2 = Note(id="n2", transcription_text="Low imp", importance_score=3.0, user_id=user_id)
    notes_res = MagicMock()
    notes_res.scalars.return_value.all.return_value = [n1, n2]
    
    db_mock.execute.side_effect = [user_res, notes_res, MagicMock()]
    
    mock_ai = AsyncMock()
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5.0}', # Step 1: Facts
        '{"stable_identity": "ID", "volatile_preferences": {}}', # Step 2: Patterns
        '[]' # Step 3: Relations
    ]
    mock_ai.clean_json_response.side_effect = lambda x: x
    mock_ai.generate_embedding.return_value = [0.1] * 1536
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai):
        
        await _process_reflection_async(user_id)
        
        # Check third AI call (relations)
        args, kwargs = mock_ai.get_chat_completion.call_args_list[2]
        prompt_content = args[0][0]["content"] if isinstance(args[0][0], dict) else args[0][1]["content"]
        
        # Should contain n1 but not n2
        assert "n1" in str(prompt_content)
        assert "n2" not in str(prompt_content)

@pytest.mark.asyncio
async def test_rag_traversal_strength_limit():
    """Test that RAG traversal ignores relations with strength <= 0.5."""
    db_mock = AsyncMock()
    user_id = "u1"
    
    # Vector results
    n_vector = Note(id="n_v", title="Vector Note", summary="V summary")
    v_res = MagicMock()
    v_res.scalars.return_value.all.return_value = [n_vector]
    
    # Relations result: one strong, one weak
    r_strong = NoteRelation(note_id1="n_v", note_id2="n_strong", strength=0.9)
    r_weak = NoteRelation(note_id1="n_v", note_id2="n_weak", strength=0.3)
    rel_res = MagicMock()
    rel_res.scalars.return_value.all.return_value = [r_strong, r_weak]
    
    # Neighbor note result
    n_neighbor = Note(id="n_strong", title="Strong Neighbor", summary="Strong summary")
    nb_res = MagicMock()
    nb_res.scalars.return_value.all.return_value = [n_neighbor]
    
    # Rag execution mocks
    db_mock.execute.side_effect = [v_res, rel_res, nb_res]
    
    with patch("app.core.rag_service.ai_service") as mock_ai:
        mock_ai.generate_embedding.return_value = [0.1]*1536
        
        context = await rag_service.get_medium_term_context(user_id, "id1", "query", db_mock)
        
        # Should contain strong but not weak
        assert "Strong summary" in context["graph"]
        assert "n_weak" not in str(db_mock.execute.call_args_list[-1]) # Checking if weak note was fetched
