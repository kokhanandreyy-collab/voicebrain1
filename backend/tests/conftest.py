import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Force safe dummy values for tests
os.environ["REDIS_URL"] = "memory://"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://localhost/voicebrain_test"
os.environ["SECRET_KEY"] = "test-secret"

# Mock redis globally before any imports
import redis
import redis.asyncio
mock_redis_obj = AsyncMock()
redis.asyncio.from_url = MagicMock(return_value=mock_redis_obj)
redis.asyncio.Redis.from_url = MagicMock(return_value=mock_redis_obj)
redis.from_url = MagicMock()
redis.Redis.from_url = MagicMock()

import types
def mock_package(name):
    m = MagicMock()
    m.__path__ = []
    # Make sure it behaves like a module?
    # MagicMock is flexible enough usually.
    sys.modules[name] = m
    
    # Link to parent if exists
    if "." in name:
        parent_name, child_name = name.rsplit(".", 1)
        if parent_name in sys.modules:
            setattr(sys.modules[parent_name], child_name, m)
            
    return m

mock_package("fastapi_mail")
mock_package("evernote")
mock_package("evernote.edam")
mock_package("evernote.edam.notestore")
mock_package("evernote.edam.type")
mock_package("evernote.edam.type.ttypes")
mock_package("evernote.edam.notestore.ttypes")
mock_package("evernote.api")
mock_package("evernote.api.client")
mock_package("oauth2")

# Notion
mock_package("notion_client")
m_errors = mock_package("notion_client.errors")
class MockAPIResponseError(Exception):
    def __init__(self, *args, **kwargs):
        self.status = 400
        self.code = "validation_error"
m_errors.APIResponseError = MockAPIResponseError

# Todoist
mock_package("todoist_api_python")
mock_package("todoist_api_python.api")
mock_package("todoist_api_python.api_async")

# Google & Slack
m_aiogoogle = mock_package("aiogoogle")
m_aiogoogle.Aiogoogle = MagicMock()
mock_package("aiogoogle.auth")
mock_package("aiogoogle.auth.creds")
mock_package("aiogoogle.models")

mock_package("slack_sdk")
mock_package("slack_sdk.web")
m_slack = mock_package("slack_sdk.web.async_client")
m_slack.AsyncWebClient = MagicMock()

# Other Integrations
mock_package("jira")
mock_package("dropbox")
mock_package("amocrm")
mock_package("amocrm.v2")
mock_package("vk_api")
mock_package("googleapiclient")
mock_package("googleapiclient.discovery")
mock_package("googleapiclient.http")
mock_package("msal")

# Global mock for RateLimiter to avoid connection issues and identifier being None
from fastapi_limiter.depends import RateLimiter
from fastapi import Request, Response
async def mock_limiter_call(self, request: Request, response: Response):
    return None
RateLimiter.__call__ = mock_limiter_call

import asyncio
import pytest
from httpx import AsyncClient
from app.main import app
from infrastructure.database import Base, get_db

@pytest.fixture(autouse=True)
def mock_db_session_factory(monkeypatch, db_session):
    # Make db_session act as its own async context manager
    db_session.__aenter__ = AsyncMock(return_value=db_session)
    db_session.__aexit__ = AsyncMock(return_value=None)
    db_session.close = AsyncMock()

    # Mock AsyncSessionLocal to return the session directly
    def get_mock_session(*args, **kwargs):
        return db_session
    
    monkeypatch.setattr("infrastructure.database.AsyncSessionLocal", get_mock_session)
    monkeypatch.setattr("workers.reflection_tasks.AsyncSessionLocal", get_mock_session)
    monkeypatch.setattr("workers.maintenance_tasks.AsyncSessionLocal", get_mock_session)
    monkeypatch.setattr("app.services.pipeline.orchestrator.AsyncSessionLocal", get_mock_session)
    
    return get_mock_session

@pytest.fixture(autouse=True)
def mock_limiter(monkeypatch):
    from infrastructure.rate_limit import limiter
    monkeypatch.setattr(limiter, "limit", lambda *args, **kwargs: lambda f: f)
    return limiter

@pytest.fixture
def db_session():
    mock = AsyncMock()
    
    # Setup standard mock behaviors for common SQLAlchemy patterns
    mock_result = MagicMock()
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    
    # We want scalars().first() to return something for test_user if we mock it that way
    # but for generic calls, empty is fine.
    
    mock.execute.return_value = mock_result
    mock.commit = AsyncMock()
    
    async def mock_refresh(obj, *args, **kwargs):
        # Populate basic fields for Pydantic validation if missing
        import uuid
        from datetime import datetime, timezone
        if hasattr(obj, 'id') and getattr(obj, 'id', None) is None:
            obj.id = str(uuid.uuid4())
        if hasattr(obj, 'created_at') and getattr(obj, 'created_at', None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if hasattr(obj, 'user_id') and getattr(obj, 'user_id', None) is None:
            obj.user_id = "test-user-uuid"
        if hasattr(obj, 'action_items') and getattr(obj, 'action_items', None) is None:
            obj.action_items = []
        if hasattr(obj, 'tags') and getattr(obj, 'tags', None) is None:
            obj.tags = []
            
    mock.refresh = AsyncMock(side_effect=mock_refresh)
    mock.add = MagicMock()
    mock.add_all = MagicMock()
    mock.delete = MagicMock()
    mock.get = AsyncMock(return_value=None)
    
    return mock

@pytest.fixture
def test_user():
    from app.models import User
    user = User(
        id="test-user-uuid",
        email="test@example.com",
        full_name="Test User",
        monthly_usage_seconds=0,
        feature_flags={"all_integrations": True}
    )
    return user

@pytest.fixture
async def client(db_session, test_user):
    from app.api.dependencies import get_current_user
    async def override_get_db():
        yield db_session
    async def override_get_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user
    
    from app.api.middleware.rate_limit import RateLimitMiddleware
    app.user_middleware = [m for m in app.user_middleware if m.cls != RateLimitMiddleware]
    # Re-build middleware stack
    app.middleware_stack = app.build_middleware_stack()

    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="session", autouse=True)
def mock_celery_app():
    with patch("app.celery_app.celery", MagicMock()):
        yield

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.lpush.return_value = True
    mock.lrange.return_value = []
    mock.delete.return_value = True
    mock.expire.return_value = True
    
    # Try to mock various redis usages
    from infrastructure.redis_client import short_term_memory
    monkeypatch.setattr(short_term_memory, "_redis", mock)
    
    # Mock FastAPI Limiter redis
    from fastapi_limiter import FastAPILimiter
    monkeypatch.setattr(FastAPILimiter, "redis", mock)
    
    return mock

@pytest.fixture(autouse=True)
def mock_celery(monkeypatch):
    from workers.analyze_tasks import process_analyze
    from workers.transcribe_tasks import process_transcribe
    from workers.reflection_tasks import reflection_daily
    
    mock_analyze = MagicMock()
    mock_transcribe = MagicMock()
    mock_reflect = MagicMock()
    
    monkeypatch.setattr(process_analyze, "delay", mock_analyze)
    monkeypatch.setattr(process_transcribe, "delay", mock_transcribe)
    monkeypatch.setattr(reflection_daily, "delay", mock_reflect)
    
    return {
        "analyze": mock_analyze,
        "transcribe": mock_transcribe,
        "reflect": mock_reflect
    }

@pytest.fixture(autouse=True)
def mock_ai_service(monkeypatch):
    from app.services.ai_service import ai_service
    
    mock_gen_emb = AsyncMock(return_value=[0.1] * 1536)
    mock_analyze = AsyncMock(return_value={
        "summary": "Mock summary",
        "action_items": ["Mock action"],
        "tags": ["mock"]
    })
    mock_ask = AsyncMock(return_value="Mock answer")
    
    monkeypatch.setattr(ai_service, "generate_embedding", mock_gen_emb)
    monkeypatch.setattr(ai_service, "analyze_text", mock_analyze)
    monkeypatch.setattr(ai_service, "ask_notes", mock_ask)
    
    return {
        "embedding": mock_gen_emb,
        "analyze": mock_analyze,
        "ask": mock_ask
    }
