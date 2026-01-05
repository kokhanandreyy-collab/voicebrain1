import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from app.models import User, Plan, Integration, PromoCode, AdminLog

@pytest.fixture
def admin_user(test_user):
    test_user.role = "admin"
    return test_user

@pytest.fixture
def normal_user(test_user):
    test_user.role = "user"
    return test_user

@pytest.mark.asyncio
async def test_admin_access_denied(client, normal_user):
    # Overwrite dependency? No, test_user fixture is used by client usually via override 
    # But here we need to ensure the user injected IS the normal user.
    # The client fixture in conftest usually uses `test_user` and overrides `get_current_user`.
    # So if we modify `test_user` in place (which is the same object if fixture scope matches), it works.
    
    normal_user.role = "user"
    response = await client.get("/admin/users")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_list_users(client, db_session, admin_user):
    admin_user.role = "admin"
    
    # Mock result
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [admin_user]
    db_session.execute.return_value = mock_res
    
    response = await client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == admin_user.email

@pytest.mark.asyncio
async def test_admin_get_stats(client, db_session, admin_user):
    admin_user.role = "admin"
    
    # We need to mock multiple await db.scalar() calls and one db.execute()
    # 1. Total Users
    # 2. Pro Users
    # 3. Premium Users
    # 4. Plans query (execute)
    # 5. Total Notes
    # 6. Active Integrations
    
    # db.scalar is called 5 times.
    db_session.scalar.side_effect = [100, 10, 5, 5000, 50] 
    
    # db.execute is called for Plans
    mock_plan = Plan(id="pro", price_monthly_rub=500)
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_plan]
    db_session.execute.return_value = mock_res
    
    response = await client.get("/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 100
    assert data["active_integrations"] == 50

@pytest.mark.asyncio
async def test_update_plan(client, db_session, admin_user):
    admin_user.role = "admin"
    
    mock_plan = Plan(id="pro", price_monthly_usd=10)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_plan
    db_session.execute.return_value = mock_res
    
    payload = {"price_monthly_usd": 15.0}
    response = await client.put("/admin/plans/pro", json=payload)
    
    assert response.status_code == 200
    assert mock_plan.price_monthly_usd == 15.0
    db_session.add.assert_called() # Check log added

@pytest.mark.asyncio
async def test_grant_subscription(client, db_session, admin_user):
    admin_user.role = "admin"
    
    target_user = User(id="u2", email="target@example.com", tier="free")
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = target_user
    db_session.execute.return_value = mock_res
    
    payload = {"tier": "pro"}
    response = await client.post("/admin/users/u2/grant_subscription", json=payload)
    
    assert response.status_code == 200
    assert target_user.tier == "pro"
    assert target_user.is_pro == True

@pytest.mark.asyncio
async def test_impersonate_user(client, db_session, admin_user):
    admin_user.role = "admin"
    
    target_user = User(id="u-target", email="target@example.com")
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = target_user
    db_session.execute.return_value = mock_res
    
    with patch("app.api.routers.admin.create_access_token", return_value="fake_token"):
        response = await client.post("/admin/impersonate/u-target")
        assert response.status_code == 200
        assert response.json()["access_token"] == "fake_token"

@pytest.mark.asyncio
async def test_ban_user(client, db_session, admin_user):
    admin_user.role = "admin"
    
    target_user = User(id="u-bad", is_active=True)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = target_user
    db_session.execute.return_value = mock_res
    
    response = await client.post("/admin/users/u-bad/ban")
    
    assert response.status_code == 200
    assert target_user.is_active == False

@pytest.mark.asyncio
async def test_create_promocode(client, db_session, admin_user):
    admin_user.role = "admin"
    
    # specific mock for uniqueness check: return None (no existing)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    payload = {"code": "SUMMER2025", "discount_percent": 50, "usage_limit": 10}
    response = await client.post("/admin/promocodes", json=payload)
    
    assert response.status_code == 200
    assert "SUMMER2025" in response.text
    db_session.add.assert_called()

@pytest.mark.asyncio
async def test_update_system_prompt(client, db_session, admin_user):
    admin_user.role = "admin"
    
    # Mock find existing logic
    # First call find prompt -> return None (create new)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    # Mock AI Service Redis
    with patch("app.services.ai_service.ai_service.redis", new_callable=AsyncMock) as mock_redis:
        payload = {"text": "You are a helpful assistant."}
        response = await client.put("/admin/prompts/default_prompt", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "default_prompt"
        assert data["text"] == "You are a helpful assistant."
        
        mock_redis.delete.assert_called_with("system_prompt:default_prompt")
