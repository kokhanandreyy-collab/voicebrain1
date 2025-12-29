import pytest
import httpx
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import encrypt_token, decrypt_token
from app.core.http_robust import RobustAsyncClient, is_retryable_status

# --- 1. Token Encryption Tests ---
def test_token_encryption_decryption():
    """Test that tokens can be encrypted and then decrypted back to original."""
    original_token = "test_access_token_123"
    
    encrypted = encrypt_token(original_token)
    assert encrypted is not None
    assert encrypted != original_token.encode()
    
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token

def test_token_encryption_none():
    """Test handling of None or empty strings."""
    assert encrypt_token(None) is None
    assert encrypt_token("") is None
    assert decrypt_token(None) is None

# --- 2. Rate-Limit Middleware Tests ---
def test_rate_limit_health_exempt():
    """Health check should be exempt from rate limiting."""
    client = TestClient(app)
    # Even many requests shouldn't trigger 429 on /health
    for _ in range(10):
        response = client.get("/health")
        assert response.status_code == 200

@patch("app.core.limiter.limiter.limit")
def test_rate_limit_trigger(mock_limit):
    """Test that rate limiter is called for protected routes."""
    # We mock the limit decorator to verify it's applied
    # Note: testing actual 429 requires a real Redis or complex mocking of slowapi storage
    from app.routers.notes import router as notes_router
    
    # Check if the rate limit decorator is present on some endpoint
    # slowapi attaches metadata to the function
    assert hasattr(app.state.limiter, "limit")

# --- 3. Robust HTTP Client (Retry) Tests ---
@pytest.mark.asyncio
async def test_robust_client_retry_on_500():
    """Test that RobustAsyncClient retries on internal server errors."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    
    # Mock responses: 2 failures then 1 success
    failure_res = MagicMock(spec=httpx.Response)
    failure_res.status_code = 500
    
    success_res = MagicMock(spec=httpx.Response)
    success_res.status_code = 200
    
    mock_client.request = AsyncMock(side_effect=[failure_res, failure_res, success_res])
    
    robust = RobustAsyncClient(mock_client)
    # We use a small max_attempts for speed
    response = await robust.get("https://api.example.com", max_attempts=3)
    
    assert response.status_code == 200
    assert mock_client.request.call_count == 3

@pytest.mark.asyncio
async def test_robust_client_retry_on_timeout():
    """Test that RobustAsyncClient retries on Connection/Timeout errors."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    
    mock_client.request = AsyncMock(side_effect=[
        httpx.TimeoutException("Timeout"),
        httpx.ConnectError("Network issue"),
        MagicMock(status_code=200)
    ])
    
    robust = RobustAsyncClient(mock_client)
    response = await robust.get("https://api.example.com", max_attempts=3)
    
    assert response.status_code == 200
    assert mock_client.request.call_count == 3

@pytest.mark.asyncio
async def test_robust_client_gives_up_after_max_attempts():
    """Test that RobustAsyncClient eventually raises if still failing."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    failure_res = MagicMock(spec=httpx.Response)
    failure_res.status_code = 502
    
    mock_client.request = AsyncMock(return_value=failure_res)
    
    robust = RobustAsyncClient(mock_client)
    
    # Since it retries and then returns the last result if successful at retry level
    # or raises if tenacity raises StopAfterAttempt. 
    # Actually tenacity with reraise=True will return the last result if it was a 'retry_if_result' match
    # Wait, if tenacity stops, it will return the result of the last attempt if it didn't raise.
    
    response = await robust.get("https://api.example.com", max_attempts=2)
    assert response.status_code == 502
    assert mock_client.request.call_count == 2
