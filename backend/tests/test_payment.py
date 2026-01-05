import pytest
import hmac
import hashlib
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from app.models import Plan, PromoCode, User, UserTier

# Helper to generate signature
def generate_signature(data, key):
    payload_keys = sorted([k for k in data.keys() if k.lower() != 'sign'])
    concat_str = "".join([str(data[k]) for k in payload_keys])
    return hmac.new(
        key.encode(),
        concat_str.encode(),
        hashlib.sha256
    ).hexdigest()

@pytest.fixture
def mock_plans(db_session):
    p1 = Plan(
        id="pro", 
        name="Pro", 
        price_monthly_usd=10.0, 
        price_yearly_usd=100.0,
        price_monthly_rub=1000.0,
        price_yearly_rub=10000.0,
        is_active=True
    )
    p2 = Plan(
        id="premium", 
        name="Premium", 
        price_monthly_usd=20.0, 
        price_yearly_usd=200.0,
        price_monthly_rub=2000.0,
        price_yearly_rub=20000.0,
        is_active=True
    )
    return [p1, p2]

@pytest.mark.asyncio
async def test_get_payment_config(client, db_session, mock_plans):
    # Mock DB response
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = mock_plans
    db_session.execute.return_value = mock_res
    
    response = await client.get("/payment/config")
    assert response.status_code == 200
    data = response.json()
    assert "usd" in data
    assert "rub" in data
    assert data["usd"]["pro"]["monthly"] == 10.0

@pytest.mark.asyncio
async def test_init_payment_dev(client, db_session, test_user, mock_plans):
    # Mock Plan lookup
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_plans[0] # Pro
    db_session.execute.return_value = mock_res
    
    payload = {
        "tier": "pro",
        "billing_period": "monthly",
        "currency": "USD"
    }
    
    # Ensure Dev Env
    with patch("infrastructure.config.settings.ENVIRONMENT", "development"), \
         patch("infrastructure.config.settings.PRODAMUS_KEY", "secret_key"):
        
        response = await client.post("/payment/init", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "dev_mock"
        assert "amount=10.0" in data["url"]

@pytest.mark.asyncio
async def test_init_payment_prod(client, db_session, test_user, mock_plans):
    # Mock Plan lookup
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_plans[0]
    db_session.execute.return_value = mock_res
    
    payload = {
        "tier": "pro",
        "billing_period": "yearly",
        "currency": "RUB"
    }
    
    # Ensure Prod Env settings logic
    with patch("infrastructure.config.settings.ENVIRONMENT", "production"), \
         patch("infrastructure.config.settings.PRODAMUS_URL", "https://pay.prodamus.ru"):
         
        response = await client.post("/payment/init", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "production"
        assert "prodamus.ru" in data["url"]
        assert "sum=10000.0" in data["url"]

@pytest.mark.asyncio
async def test_init_payment_invalid_tier(client, db_session, test_user):
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db_session.execute.return_value = mock_res
    
    payload = {"tier": "invalid", "billing_period": "monthly"}
    response = await client.post("/payment/init", json=payload)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_payment_webhook_success(client, db_session, test_user, mock_plans):
    # Setup Data
    secret_key = "test_prodamus_key"
    data = {
        "order_id": "123",
        "customer_email": "test@example.com",
        "payment_status": "success",
        "sum": "1000.0",
        "tier": "pro", # Legacy/Fallback field check
        "#tier": "pro",
        "#period": "monthly",
        "#currency": "RUB"
    }
    sign = generate_signature(data, secret_key)
    data["Sign"] = sign
    
    # Mock Plan and User lookup
    # 1. Plan lookup (for price check call)
    # 2. User lookup (for upgrade)
    
    def mock_execute(query, *args, **kwargs):
        q_str = str(query).lower()
        res = MagicMock()
        res.scalars = MagicMock()
        if "from plans" in q_str:
            res.scalars.return_value.first.return_value = mock_plans[0] # Pro
        elif "from users" in q_str:
             res.scalars.return_value.first.return_value = test_user
        else:
             res.scalars.return_value.first.return_value = None
        return res
        
    db_session.execute.side_effect = mock_execute
    
    with patch("infrastructure.config.settings.PRODAMUS_KEY", secret_key):
        # request.form() usage in FastAPI requires posting form data
        response = await client.post("/payment/webhook", data=data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert test_user.tier == UserTier.PRO

@pytest.mark.asyncio
async def test_payment_webhook_bad_sign(client):
    data = {"order_id": "123", "Sign": "bad_sign"}
    with patch("infrastructure.config.settings.PRODAMUS_KEY", "secret"):
        response = await client.post("/payment/webhook", data=data)
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_payment_webhook_price_mismatch(client, db_session, test_user, mock_plans):
    secret_key = "key"
    data = {
        "payment_status": "success",
        "sum": "1.0", # Wrong price, expected 1000
        "#tier": "pro",
        "#period": "monthly",
        "#currency": "RUB"
    }
    sign = generate_signature(data, secret_key)
    data["Sign"] = sign
    
    # Mock Plan
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_plans[0]
    db_session.execute.return_value = mock_res
    
    with patch("infrastructure.config.settings.PRODAMUS_KEY", secret_key):
        response = await client.post("/payment/webhook", data=data)
        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"]

@pytest.mark.asyncio
async def test_dev_upgrade(client, db_session, test_user):
    # Mock User
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = test_user
    db_session.execute.return_value = mock_res
    
    with patch("infrastructure.config.settings.ENVIRONMENT", "development"):
        response = await client.post("/payment/dev/upgrade?email=test@example.com&tier=premium")
        assert response.status_code == 200
        assert test_user.tier == UserTier.PREMIUM

@pytest.mark.asyncio
async def test_dev_upgrade_forbidden(client):
    with patch("infrastructure.config.settings.ENVIRONMENT", "production"):
        response = await client.post("/payment/dev/upgrade?email=t&tier=p")
        assert response.status_code == 403
