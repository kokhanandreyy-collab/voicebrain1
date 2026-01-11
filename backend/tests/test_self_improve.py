
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tasks.self_improve import _process_improvement_async
from app.models import LongTermMemory

@pytest.mark.asyncio
async def test_self_improvement_logic():
    """Test memory merging and cleanup."""
    
    mock_db = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_db
    mock_ctx.__aexit__.return_value = None
    
    # Mock data
    m1 = LongTermMemory(id="1", summary_text="I like cats.", importance_score=5.0)
    m2 = LongTermMemory(id="2", summary_text="I love felines.", importance_score=6.0)
    m3 = LongTermMemory(id="3", summary_text="I hate animals.", importance_score=2.0)
    
    # Select returns proper scalar
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [m1, m2, m3]
    mock_db.execute.return_value = mock_res
    
    # Mock AI response
    mock_ai_resp = """
    {
        "merged_groups": [["1", "2"]],
        "contradictions_to_remove": ["3"]
    }
    """
    
    with patch("tasks.self_improve.AsyncSessionLocal", return_value=mock_ctx), \
         patch("tasks.self_improve.ai_service", new_callable=AsyncMock) as mock_ai, \
         patch("tasks.self_improve.logger") as mock_logger:
        
        # ai_service.clean_json_response is likely synchronous, so we mock it as MagicMock
        mock_ai.clean_json_response = MagicMock(return_value=mock_ai_resp)
        
        # 1. get_chat_completion first call: Logic
        # 2. get_chat_completion second call: Summary of merged
        mock_ai.get_chat_completion.side_effect = [
            mock_ai_resp, 
            "I really enjoy cats."
        ]
        
        await _process_improvement_async("user1")
        
        # Debug errors
        if mock_logger.error.called:
             print(f"ERROR LOGGED: {mock_logger.error.call_args}")
        
        # Verify MERGE
        assert m1.is_archived == True
        assert m2.is_archived == True
        
        # Verify NEW ADDITION
        # db.add called with new memory
        assert mock_db.add.called
        args = mock_db.add.call_args[0][0]
        assert args.summary_text == "I really enjoy cats."
        assert args.source == "refined"
        
        # Verify CONTRADICTION REMOVAL
        assert m3.is_archived == True
