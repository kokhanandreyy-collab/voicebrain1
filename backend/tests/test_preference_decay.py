import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workers.reflection_tasks import _process_reflection_async
from app.models import User, Note
import datetime
import json

@pytest.mark.asyncio
async def test_preference_decay():
    """
    Test decay logic for adaptive preferences.
    """
    user_id = "u1"
    
    # Needs explicit timezone for comparisons
    now = datetime.datetime.now(datetime.timezone.utc)
    old_date = now - datetime.timedelta(days=60) # 60 days old
    recent_date = now - datetime.timedelta(days=1)
    
    # Initial Preferences
    initial_prefs = {
        "legacy_key": "legacy_val", # Should convert to obj, updated now (days=0, conf=1.0)
        "old_key": {
            "value": "old_val",
            "confidence": 0.5, # Should decay. 60 days / 30 = 2 decay factors. exp(-2) ~= 0.135. 0.5 * 0.135 = 0.06 < 0.4 -> Remove
            "updated_at": old_date.isoformat()
        },
        "stable_key": {
            "value": "stable_val",
            "confidence": 1.0,
            "updated_at": recent_date.isoformat() # 1 day old. exp(-1/30) ~= 0.96. 1.0 -> 0.96. Keep.
        }
    }
    
    # Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    
    # 1. Notes (Empty so we skip reflection AI part? No, if no notes, function returns early)
    # We MUST have notes to reach the preference/identity logic.
    n1 = Note(id="n1", user_id=user_id, transcription_text="Some text", created_at=now)
    mock_note_res = MagicMock()
    mock_note_res.scalars.return_value.all.return_value = [n1]
    
    # 2. Cache Miss (return None)
    mock_cache_res = MagicMock()
    mock_cache_res.scalars.return_value.first.return_value = None
    
    # 3. User Fetch (for update)
    user = User(id=user_id, adaptive_preferences=initial_prefs)
    mock_user_res = MagicMock()
    mock_user_res.scalars.return_value.first.return_value = user
    
    # Setup Sequence
    # Call 1: Monitor Node Count
    # Call 2: Monitor Edge Count
    # Call 3: Notes Fetch
    # Call 4: Cache Lookup
    # Call 5: User Fetch
    
    mock_nodes_res = MagicMock()
    mock_nodes_res.scalar.return_value = 0
    mock_edges_res = MagicMock()
    mock_edges_res.scalar.return_value = 0

    mock_db.execute.side_effect = [
        mock_nodes_res, mock_edges_res, # Monitoring
        mock_note_res, # Notes
        mock_cache_res, # Cache
        mock_user_res, # User fetch
        # Others (Graph rels maybe? Graph fetch uses execute)
        MagicMock() 
    ]
    
    # Mock AI Service
    # Return JSON with identity_summary to trigger the update block
    mock_ai_resp = json.dumps({
        "summary": "Summary",
        "identity_summary": "New ID",
        "importance_score": 5,
        "confidence": 0.9,
        "source": "fact"
    })
    mock_graph_resp = "[]" # Empty list for graph
    
    with patch("workers.reflection_tasks.AsyncSessionLocal") as mock_session_cls, \
         patch("workers.reflection_tasks.ai_service.generate_embedding", new_callable=AsyncMock) as mock_gen_emb, \
         patch("workers.reflection_tasks.ai_service.get_embedding", new_callable=AsyncMock) as mock_get_emb, \
         patch("workers.reflection_tasks.ai_service.get_chat_completion", new_callable=AsyncMock) as mock_chat:
         
         mock_session_cls.return_value.__aenter__.return_value = mock_db
         mock_gen_emb.return_value = [0.1]*1536
         mock_get_emb.return_value = [0.1]*1536
         mock_chat.side_effect = [mock_ai_resp, mock_graph_resp]
         
         await _process_reflection_async(user_id)
         
         # Verification
         updated_prefs = user.adaptive_preferences
         print(f"DEBUG PREFS: {updated_prefs}")
         
         # Check for conversion
         if isinstance(updated_prefs.get("legacy_key"), str):
             pytest.fail(f"Legacy key not migrated! Prefs: {updated_prefs}")
         
         # 1. Legacy Check
         assert "legacy_key" in updated_prefs
         assert updated_prefs["legacy_key"]["confidence"] == 1.0 # Recently migrated
         
         # 2. Old Key Check (Should be removed)
         assert "old_key" not in updated_prefs
         
         # 3. Stable Key Check (Decayed slightly but kept)
         assert "stable_key" in updated_prefs
         assert updated_prefs["stable_key"]["confidence"] < 1.0
         assert updated_prefs["stable_key"]["confidence"] > 0.9
