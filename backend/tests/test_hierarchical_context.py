import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.core.rag_service import rag_service
from app.models import Note, LongTermMemory

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_hierarchical_context_content(mock_db_session):
    """Test standard hierarchical context content without complex logic."""
    note = Note(id="current", user_id="u1", transcription_text="Hello", created_at=datetime.utcnow())
    
    # Setup Mocks for DB calls
    # 1. Short Term (Notes)
    st_notes = [Note(id="n1", summary="ShortTerm1", created_at=datetime(2025, 1, 1))]
    mock_st_res = MagicMock()
    mock_st_res.scalars().all.return_value = st_notes
    
    # 2. Medium Term (Vector Search) 
    # This is called inside get_medium_term_context. 
    # We will mock get_medium_term_context directly to simplify unit testing logic complexity.
    
    # 3. Long Term (LTM)
    lt_mems = [LongTermMemory(summary_text="LongTerm1", importance_score=9.0)]
    mock_lt_res = MagicMock()
    mock_lt_res.scalars().all.return_value = lt_mems
    
    # Mock DB Execute Sequence for build_hierarchical_context main logic (Short and Long).
    # Medium is mocked away.
    mock_db_session.execute.side_effect = [mock_st_res, mock_lt_res]
    
    with patch.object(rag_service, 'get_medium_term_context', new_callable=AsyncMock) as mock_medium:
        mock_medium.return_value = {"vector": "MediumTerm1", "graph": ""}
        
        context = await rag_service.build_hierarchical_context(note, mock_db_session)
        
        # Verify Content
        assert "ShortTerm1" in context
        assert "MediumTerm1" in context
        assert "LongTerm1" in context
        
        # Verify Structure Labels
        assert "Short-term context" in context
        assert "Recent context" in context
        assert "Long-term knowledge" in context
