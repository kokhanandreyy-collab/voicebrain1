import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.maintenance_tasks import _cleanup_memory_async
from app.models import NoteRelation

@pytest.mark.asyncio
async def test_cleanup_weak_relations():
    """Test that weak relations are deleted."""
    
    mock_db = AsyncMock()
    
    # Setup Mocks to ignore Note/LTM part (return empty lists)
    mock_notes_res = MagicMock()
    mock_notes_res.scalars().all.return_value = []
    
    mock_ltm_res = MagicMock()
    mock_ltm_res.scalars().all.return_value = []
    
    # Setup Relations
    # r1: weak (0.1) -> should delete
    # r2: weak (0.29) -> should delete
    # r3: strong (0.3) -> keep (assuming < 0.3)
    r1 = NoteRelation(id="r1", strength=0.1)
    r2 = NoteRelation(id="r2", strength=0.29)
    # The select query in code will only fetch strength < 0.3. 
    # So we should assume DB returns r1 and r2.
    
    mock_rel_res = MagicMock()
    mock_rel_res.scalars().all.return_value = [r1, r2]
    
    mock_db.execute.side_effect = [mock_notes_res, mock_ltm_res, mock_rel_res]
    
    with patch("workers.maintenance_tasks.AsyncSessionLocal") as mock_session_cls:
         mock_session_cls.return_value = mock_db
         
         await _cleanup_memory_async()
         
         # Check deletions
         deleted_items = [call.args[0] for call in mock_db.delete.call_args_list]
         
         assert r1 in deleted_items
         assert r2 in deleted_items
         assert len(deleted_items) == 2
