import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import Note, NoteEmbedding, LongTermMemory, NoteRelation
from app.core.rag_service import rag_service

@pytest.mark.asyncio
async def test_embed_note(db_session, mock_ai_service):
    note = Note(id="note_1", title="Title", summary="Summary", transcription_text="Text", tags=["tag"], user_id="u1")
    db_session.add(note)
    await db_session.commit()
    
    mock_ai_service["embedding"].return_value = [0.1] * 1536
    
    # Configure mock to return an embedding when queried
    mock_emb = NoteEmbedding(note_id=note.id, user_id=note.user_id, embedding=[0.1]*1536)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_emb
    db_session.execute = AsyncMock(return_value=mock_result)

    await rag_service.embed_note(note, db_session)
    await db_session.commit()
    
    # Check if embedding saved
    from sqlalchemy.future import select
    res = await db_session.execute(select(NoteEmbedding).where(NoteEmbedding.note_id == "note_1"))
    emb = res.scalars().first()
    assert emb is not None
    assert mock_ai_service["embedding"].called

@pytest.mark.asyncio
async def test_medium_term_retrieval(db_session, test_user, mock_ai_service):
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Setup similar notes and relations
    n1 = Note(id="n1", user_id=test_user.id, title="Reference", summary="Reference summary", created_at=now, importance_score=5.0)
    n2 = Note(id="n2", user_id=test_user.id, title="Related", summary="Related summary", created_at=now, importance_score=5.0)
    db_session.add_all([n1, n2])
    await db_session.commit()
    
    # Add embeddings
    emb1 = NoteEmbedding(note_id=n1.id, user_id=test_user.id, embedding=[0.1]*1536)
    emb2 = NoteEmbedding(note_id=n2.id, user_id=test_user.id, embedding=[0.2]*1536)
    db_session.add_all([emb1, emb2])
    
    # Add relation
    rel = NoteRelation(note_id1=n1.id, note_id2=n2.id, relation_type="related", strength=0.8, confidence=0.9, source="inferred")
    db_session.add(rel)
    await db_session.commit()
    
    # configure mock to return these for vector search and graph search
    mock_result_vector = MagicMock()
    mock_result_vector.scalars.return_value.all.return_value = [n1]

    mock_result_graph = MagicMock()
    mock_result_graph.scalars.return_value.all.return_value = [rel]

    mock_result_neighbor = MagicMock()
    mock_result_neighbor.scalars.return_value.all.return_value = [n2]
    
    # We need to handle multiple execute calls
    # 1. Vector Search, 2. Graph Relations, 3. Neighbor Notes fetch
    db_session.execute.side_effect = [mock_result_vector, mock_result_graph, mock_result_neighbor]
    
    mock_ai_service["embedding"].return_value = [0.1] * 1536
    
    context = await rag_service.get_medium_term_context(test_user.id, "current_note_id", "query text", db_session)
    
    assert "Reference summary" in context["vector"]
    assert "Related summary" in context["graph"]

@pytest.mark.asyncio
async def test_long_term_memory_retrieval(db_session, test_user, mock_ai_service):
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    
    m1 = LongTermMemory(
        user_id=test_user.id, 
        summary_text="Crucial info", 
        importance_score=10.0, 
        embedding=[0.1]*1536,
        created_at=now,
        confidence=0.9,
        source="fact"
    )
    m2 = LongTermMemory(
        user_id=test_user.id, 
        summary_text="Minor info", 
        importance_score=2.0, 
        embedding=[0.9]*1536,
        created_at=now,
        confidence=0.9,
        source="inferred"
    )
    db_session.add_all([m1, m2])
    await db_session.commit()
    
    # configure mock to return these
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [m1, m2]
    db_session.execute = AsyncMock(return_value=mock_result)
    
    # Search with high relevance to m2 but m1 has higher importance
    mock_ai_service["embedding"].return_value = [0.9] * 1536
    
    # get_long_term_memory sorts by (importance_score, created_at) after initial top 50 relevance
    context = await rag_service.get_long_term_memory(test_user.id, db_session, query_text="topic")
    
    assert "Crucial info" in context
    assert "Score: 10.0" in context
