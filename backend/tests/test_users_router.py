import pytest
from unittest.mock import MagicMock, AsyncMock
from app.api.routers.v1.users import UserStats

@pytest.mark.asyncio
async def test_get_current_user_profile(client, test_user):
    test_user.bio = "Original Bio"
    test_user.target_language = "Spanish"
    
    response = await client.get("/users/me")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "Original Bio"
    assert data["target_language"] == "Spanish"
    assert data["email"] == test_user.email

@pytest.mark.asyncio
async def test_update_user_profile(client, test_user, db_session):
    payload = {
        "bio": "New Bio",
        "target_language": "French"
    }
    
    response = await client.put("/users/me", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "New Bio"
    assert data["target_language"] == "French"
    
    # Verify DB update in memory object and session call
    assert test_user.bio == "New Bio"
    assert test_user.target_language == "French"
    db_session.commit.assert_called()
    db_session.refresh.assert_called_with(test_user)

@pytest.mark.asyncio
async def test_user_stats_basic(client, test_user, db_session):
    test_user.tier = "free"
    
    # Mock db.scalar results for counts
    # scalar() is called twice: count(Note), sum(Duration)
    # We configure side_effect
    db_session.scalar = AsyncMock(side_effect=[
        10, # Total Notes
        600 # Total Duration (10 mins)
    ])
    
    # Mock Plan query (empty -> fallback)
    # db.execute for Plan
    mock_plan_res = MagicMock()
    mock_plan_res.scalars.return_value.first.return_value = None
    
    # Mock Recent Notes (dates)
    mock_notes_res = MagicMock()
    mock_notes_res.scalars.return_value.all.return_value = [] # No recent notes mostly
    
    # Mock Integration Usage
    mock_logs_res = MagicMock()
    mock_logs_res.all.return_value = [("notion", 5)]
    
    # db.execute calls:
    # 1. Plan
    # 2. Recent Notes (dates)
    # 3. Integration Usage
    db_session.execute = AsyncMock(side_effect=[
        mock_plan_res,
        mock_notes_res,
        mock_logs_res
    ])
    
    response = await client.get("/users/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify mapping
    assert data["total_notes"] == 10
    assert data["saved_time_minutes"] == 30 # (600 * 3) / 60
    assert data["integration_usage"] == [{"name": "notion", "value": 5}]
