import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.infrastructure.database import Base, get_db
from app.infrastructure.config import settings

# Test Database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("voicebrain_db", "voicebrain_test")

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
    # from fastapi_limiter import FastAPILimiter
    # import redis.asyncio as redis
    # from app.routers.notes import RateLimiter # Path likely changed?
    # Actually routers are in app.api.routers now.
    from app.infrastructure.rate_limit import limiter
    # We can't easily mock limiter instance but we can mock the dependency if used.
    # But usually limiter is global. 
    # Let's just yield client.
    
    async with AsyncClient(app=app, base_url="http://test/api/v1") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Mocks
@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    from app.infrastructure.storage import storage_client
    async def mock_upload(file_obj, key, **kwargs):
        return f"http://mock-s3.local/{key}"
    monkeypatch.setattr(storage_client, "upload_file", mock_upload)

@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    from app.services.email import send_email
    async def mock_send(email, subject, body):
        return True
    monkeypatch.setattr("app.services.email.send_email", mock_send)
