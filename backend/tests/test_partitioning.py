
import pytest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.rag_service import rag_service
from app.models import Note, NoteEmbedding, LongTermMemory

@pytest.mark.asyncio
async def test_embed_note_uses_partition_key():
    """Test that embed_note uses user_id in queries (partition pruning trigger)."""
    
    note = Note(
        id="note_1",
        user_id="user_123", # Ensure this is string
        title="Test Note",
        summary="Test Summary",
        transcription_text="Test transcription",
        tags=["tag1"]
    )
    
    mock_db = AsyncMock()
    # Setup mock result for existing check (return None means create new)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    
    with patch("app.core.rag_service.logger") as mock_logger, \
         patch("app.core.rag_service.ai_service") as mock_ai:
        
        # FIX: Ensure it returns an awaitable (AsyncMock)
        mock_ai.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        
        await rag_service.embed_note(note, mock_db)
        
        if not mock_db.add.called:
             # Just in case it fails again, print why
             error_calls = [str(c[0]) for c in mock_logger.error.call_args_list]
             pytest.fail(f"db.add not called. Errors: {error_calls}")

        args, _ = mock_db.add.call_args
        embedding_obj = args[0]
        assert isinstance(embedding_obj, NoteEmbedding)
        assert embedding_obj.note_id == "note_1"
        assert embedding_obj.user_id == "user_123"
        
        mock_logger.info.assert_any_call("Using partition for user_id=user_123 in embed_note")


@pytest.mark.asyncio
async def test_long_term_memory_partition_logging():
    user_id = "user_456"
    mock_db = AsyncMock()
    
    with patch("app.core.rag_service.logger") as mock_logger, \
         patch("app.core.rag_service.ai_service") as mock_ai:
        
        mock_ai.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await rag_service.get_long_term_memory(user_id, mock_db, query_text="Some query")
        
        mock_logger.info.assert_any_call(f"Using partition for user_id={user_id} in get_long_term_memory search")
