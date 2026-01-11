import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from app.core.analyze_core import analyze_core
from app.models import Note, User, CachedIntent

@pytest.mark.asyncio
async def test_intent_cache_hit():
    """Test that a simple intent command uses the cache without AI."""
    db_mock = AsyncMock()
    user = User(id="u1", stable_identity="")
    note = Note(id="n1", user_id="u1", transcription_text="Запиши задачу: Купить хлеб")
    
    # Mock cache hit
    cached_action = {
        "intent": "create_task",
        "title": "Buy Bread",
        "summary": "Task to buy bread",
        "action_items": ["Buy bread"]
    }
    
    entry_mock = CachedIntent(action_json=cached_action)
    res_mock = MagicMock()
    res_mock.scalars.return_value.first.return_value = entry_mock
    db_mock.execute.return_value = res_mock
    
    with patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="ctx"), \
         patch("app.core.analyze_core.ai_service") as mock_ai:
        
        analysis, cache_hit = await analyze_core.analyze_step(note, user, db_mock, MagicMock())
        
        assert cache_hit is True
        assert analysis["intent"] == "create_task"
        assert note.title == "Buy Bread"
        # DeepSeek (analyze_text) should NOT be called
        mock_ai.analyze_text.assert_not_called()

@pytest.mark.asyncio
async def test_intent_cache_miss_and_save():
    """Test that a new simple intent command is saved to cache after AI call."""
    db_mock = AsyncMock()
    user = User(id="u1", stable_identity="")
    note = Note(id="n1", user_id="u1", transcription_text="Запиши задачу: Купить молоко")
    
    # 1. Intent cache miss
    res_intent = MagicMock()
    res_intent.scalars.return_value.first.return_value = None
    
    # 2. Semantic cache miss
    res_semantic = MagicMock()
    res_semantic.scalars.return_value.first.return_value = None
    
    db_mock.execute.side_effect = [res_intent, res_semantic, MagicMock()] # Lookup, Lookup, Update User
    
    mock_ai = AsyncMock()
    mock_ai.generate_embedding.return_value = [0.1]*1536
    mock_ai.analyze_text.return_value = {
        "intent": "create_task",
        "title": "Buy Milk",
        "summary": "Task to buy milk"
    }
    
    with patch("app.core.analyze_core.rag_service.build_hierarchical_context", return_value="ctx"), \
         patch("app.core.analyze_core.ai_service", mock_ai):
        
        await analyze_core.analyze_step(note, user, db_mock, MagicMock())
        
        # Verify AI called
        mock_ai.analyze_text.assert_called_once()
        
        # Verify CachedIntent was added to DB
        added_objects = [call.args[0] for call in db_mock.add.call_args_list]
        assert any(isinstance(obj, CachedIntent) for obj in added_objects)
        
        # Verify TTL is 7 days
        cached_intent = next(obj for obj in added_objects if isinstance(obj, CachedIntent))
        assert cached_intent.expires_at > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=6)
