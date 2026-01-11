import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import User
from tasks.reflection import _process_reflection_async

@pytest.mark.asyncio
async def test_gated_identity_update():
    """Test that identity only updates if cosine similarity is < 0.85."""
    user_id = "u1"
    user = User(
        id=user_id, 
        stable_identity="Old Identity", 
        identity_embedding=[1.0, 0.0], # Simplified 2D vector
        emotion_history=[]
    )
    
    # DB Mock
    m_notes_scalar = MagicMock()
    m_notes_scalar.all.return_value = [] # No notes prevents entry? No, we check notes.
    # We need notes to proceed.
    import datetime
    from app.models import Note
    n1 = Note(id="n1", transcription_text="t1", importance_score=8.0, created_at=datetime.datetime.now(datetime.timezone.utc))
    m_notes_scalar.all.return_value = [n1]

    db_mock = AsyncMock()
    
    # Mocking execute carefully
    m_user_scalar = MagicMock()
    m_user_scalar.first.return_value = user
    
    m_count = MagicMock()
    m_count.scalar.return_value = 1
    
    def exec_side_effect(stmt):
        s = str(stmt).lower()
        if "from users" in s:
            r = MagicMock()
            r.scalars.return_value = m_user_scalar
            return r
        if "from notes" in s:
             r = MagicMock()
             r.scalars.return_value = m_notes_scalar
             return r
        if "count" in s:
             r = MagicMock()
             r.scalars.return_value = m_count
             return r
        return MagicMock()
        
    db_mock.execute.side_effect = exec_side_effect
    db_mock.__aenter__.return_value = db_mock # For async with
    db_mock.__aexit__.return_value = None

    # AI Service Mock
    mock_ai = AsyncMock()
    mock_ai.clean_json_response = MagicMock(side_effect=lambda x: x)
    
    # SCENARIO 1: High Similarity (No Update)
    # New Identity Embedding = [0.9, 0.1] -> Sim ~0.99
    # Step 1 (Values), Step 2 (Patterns), Step 3 (Graph)
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5}',
        '{"stable_identity": "New Identity Similar", "volatile_preferences": {}, "current_emotion": "Happy"}',
        '[]'
    ]
    
    embed_map = {
        "New Identity Similar": [0.99, 0.01], # Very close to [1.0, 0.0]
        "New Identity Different": [0.0, 1.0]  # Orthogonal, Sim = 0
    }
    mock_ai.generate_embedding.side_effect = lambda text: embed_map.get(text, [0.1]*1536)

    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor"):
         
        await _process_reflection_async(user_id)
        
        # Check: Identity should NOT change because similarity is high
        assert user.stable_identity == "Old Identity"
        # Check: Emotion appended
        assert len(user.emotion_history) == 1
        assert user.emotion_history[0]["emotion"] == "Happy"

    # SCENARIO 2: Low Similarity (Update)
    mock_ai.get_chat_completion.side_effect = [
        '{"facts_summary": "fact", "importance_score": 5}',
        '{"stable_identity": "New Identity Different", "volatile_preferences": {}, "current_emotion": "Sad"}',
        '[]'
    ]
    
    with patch("tasks.reflection.AsyncSessionLocal", return_value=db_mock), \
         patch("tasks.reflection.ai_service", mock_ai), \
         patch("tasks.reflection.monitor"):
         
        await _process_reflection_async(user_id)
        
        # Check: Identity SHOULD change
        assert user.stable_identity == "New Identity Different"
        assert user.identity_embedding == [0.0, 1.0]
        # Check: Emotion appended (now 2)
        assert len(user.emotion_history) == 2
        assert user.emotion_history[1]["emotion"] == "Sad"
