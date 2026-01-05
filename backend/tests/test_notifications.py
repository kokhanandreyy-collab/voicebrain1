import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_subscribe_push_notification(client, test_user, db_session):
    # Initial state
    test_user.push_subscriptions = []
    
    payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
        "keys": {
            "p256dh": "key1",
            "auth": "auth1"
        }
    }
    
    response = await client.post("/notifications/subscribe", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"status": "subscribed"}
    
    # Verify DB update
    assert len(test_user.push_subscriptions) == 1
    assert test_user.push_subscriptions[0]["endpoint"] == payload["endpoint"]
    db_session.add.assert_called_with(test_user)
    db_session.commit.assert_called()

@pytest.mark.asyncio
async def test_subscribe_duplicate_endpoint(client, test_user, db_session):
    # Pre-populate
    existing_sub = {
        "endpoint": "https://existing.com",
        "keys": {"auth": "xyz"}
    }
    test_user.push_subscriptions = [existing_sub]
    
    # Try to add same endpoint again
    payload = {
        "endpoint": "https://existing.com",
        "keys": {"auth": "xyz"}
    }
    
    response = await client.post("/notifications/subscribe", json=payload)
    
    assert response.status_code == 200
    
    # Logic in notifications.py checks existence by endpoint
    # and only appends if not exists
    assert len(test_user.push_subscriptions) == 1 
    # db.add/commit depends on implementation logic logic (if not exists -> add)
    # If exists, it might skip db ops or just return success
