import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async  
from app.models import Note, CachedAnalysis
import datetime
import hashlib

@pytest.mark.asyncio
async def test_smart_cache_hit():
    """
    Test that reflection uses cache_key for lookup and hits if key matches.
    """
    user_id = "u1"
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Notes
    n1 = Note(id="n1", user_id=user_id, transcription_text="Text content", created_at=now)
    # Content Hash: sha256("...Text: Text content")
    notes_text = f"Date: {now}\nText: Text content"
    content_hash = hashlib.sha256(notes_text.encode()).hexdigest()
    
    # User Identity Version
    id_ver = "v0" # Mock returns v0 if no update
    smart_key = hashlib.sha256(f"{content_hash}|{id_ver}".encode()).hexdigest()
    
    # Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    mock_nodes_res = MagicMock()
    mock_nodes_res.scalar.return_value = 0
    mock_edges_res = MagicMock()
    mock_edges_res.scalar.return_value = 0
    
    mock_note_res = MagicMock()
    mock_note_res.scalars.return_value.all.return_value = [n1]
    
    # Mock User Identity Fetch (Call BEFORE cache check now)
    mock_user_info = MagicMock()
    mock_user_info.identity_updated_at = None
    mock_user_info_res = MagicMock()
    mock_user_info_res.first.return_value = mock_user_info
    
    # Mock Cache Lookup (HIT)
    cached_entry = CachedAnalysis(cache_key=smart_key, result={"summary": "Cached"})
    mock_cache_res = MagicMock()
    mock_cache_res.scalars.return_value.first.return_value = cached_entry
    
    mock_db.execute.side_effect = [
        mock_nodes_res, mock_edges_res, # monitor
        mock_note_res, # notes
        mock_user_info_res, # identity ver (NEW CALL)
        mock_cache_res, # cache check
    ]
    
    with patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls, \
         patch("workers.reflection_tasks.ai_service.generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch("workers.reflection_tasks.track_cache_hit") as mock_hit_track:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         
         await _process_reflection_async(user_id)
         
         # Verify Cache Hit tracked
         mock_hit_track.assert_called_with("reflection")
         # Verify AI NOT called (no embedding needed if hit? Wait, logic gen embedding ONLY if miss? Yes, inside exception block or else branch)
         # Actually generating embedding moved to `if miss`.
         mock_emb.assert_not_called()

@pytest.mark.asyncio
async def test_smart_cache_miss():
    """
    Test cache miss scenarios.
    """
    user_id = "u1"
    now = datetime.datetime.now(datetime.timezone.utc)
    n1 = Note(id="n1", user_id=user_id, transcription_text="Text content", created_at=now)
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    mock_nodes_res = MagicMock()
    mock_nodes_res.scalar.return_value = 0
    mock_edges_res = MagicMock()
    mock_edges_res.scalar.return_value = 0
    mock_note_res = MagicMock()
    mock_note_res.scalars.return_value.all.return_value = [n1]
    
    mock_user_info_res = MagicMock()
    mock_user_info_res.first.return_value = MagicMock(identity_updated_at=None)
    
    # Cache Miss
    mock_cache_res = MagicMock()
    mock_cache_res.scalars.return_value.first.return_value = None
    
    # User Fetch (for update)
    mock_user_res = MagicMock()
    mock_user_res.scalars.return_value.first.return_value = MagicMock()

    mock_db.execute.side_effect = [
        mock_nodes_res, mock_edges_res,
        mock_note_res,
        mock_user_info_res,
        mock_cache_res, # miss
        mock_user_res, # update
        # other calls...
    ]
    
    mock_ai_resp = '{"summary": "New"}'
    
    with patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls, \
         patch("workers.reflection_tasks.ai_service.generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch("workers.reflection_tasks.ai_service.get_chat_completion", new_callable=AsyncMock) as mock_chat, \
         patch("workers.reflection_tasks.track_cache_miss") as mock_miss_track:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         mock_emb.return_value = [0.1]*1536
         mock_chat.return_value = mock_ai_resp
         # Mock graph call too if needed, or side effect. 
         # Assuming clean_json works on mock_ai_resp.
         # Graph call will happen.
         # Let's ensure mock_chat handles sequence.
         
         await _process_reflection_async(user_id)
         
         mock_miss_track.assert_called_with("reflection")
         mock_emb.assert_called() # Should generate embedding on miss
