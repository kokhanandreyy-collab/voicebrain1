import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
import os

# Test Database URL (Use a separate DB or suffix)
# For simplicity in this env, we'll try to use a 'voicebrain_test' database if it exists,
# or just override the main one if we are careful (not recommended).
# Better: Use sqlite for basic integration tests if we mock the vector search.
# BUT user asked for integration test including Upload -> processing check.
# We will use Postgres with a 'test' suffix to support pgvector.
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "").replace("voicebrain_db", "voicebrain_test")
if not TEST_DATABASE_URL:
    TEST_DATABASE_URL = "postgresql+asyncpg://voicebrain:voicebrain_secret@db:5432/voicebrain_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Create tables
    async with engine.begin() as conn:
        # Note: In a real environment, you'd check for pgvector extension here
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def async_client(db_session):
    # Override get_db
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock RateLimiter to avoid Redis dependency during tests
    from fastapi_limiter import FastAPILimiter
    import redis.asyncio as redis
    # We can just not init it or mock the dependency
    from app.routers.notes import RateLimiter
    app.dependency_overrides[RateLimiter] = lambda: None

    async with AsyncClient(app=app, base_url="http://test/api/v1") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Mocks
@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    from app.core.storage import storage_client
    async def mock_upload(file_obj, key, **kwargs):
        return f"http://mock-s3.local/{key}"
    monkeypatch.setattr(storage_client, "upload_file", mock_upload)

@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    from app.services.email import send_email
    async def mock_send(email, subject, body):
        return True
    monkeypatch.setattr("app.services.email.send_email", mock_send)
