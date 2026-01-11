
import pytest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.cleanup_memory import run_cleanup
from app.models import NoteRelation

@pytest.mark.asyncio
async def test_graph_cleanup_constraints():
    """Test that cleanup removes old and weak relations."""
    mock_session = AsyncMock()
    
    # Setup mock results
    mock_res = MagicMock()
    mock_res.rowcount = 5
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar.return_value = 10
    
    mock_session.execute.return_value = mock_res
    
    # We must properly mock AsyncSessionLocal as context manager
    mock_db_ctx = MagicMock()
    mock_db_ctx.__aenter__.return_value = mock_session
    mock_db_ctx.__aexit__.return_value = None
    
    with patch("tasks.cleanup_memory.AsyncSessionLocal", return_value=mock_db_ctx), \
         patch("tasks.cleanup_memory.monitor"):
        
        await run_cleanup()
         
        # Verify sql execution
        # We expect multiple execute calls
        assert mock_session.execute.call_count >= 5
        
        # Verify we are targeting NoteRelation
        # We can inspect the SQL string representation or table
        calls = mock_session.execute.call_args_list
        found_rel_delete = False
        for call in calls:
            stmt = call[0][0]
            # Simple check if statement involves note_relations
            if "note_relations" in str(stmt):
                found_rel_delete = True
        
        assert found_rel_delete
