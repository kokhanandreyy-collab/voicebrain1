import pytest
from httpx import AsyncClient
from app.main import app
from app.models import LongTermMemory, User

@pytest.mark.asyncio
async def test_reject_memory(db_session, test_user):
    """Test user rejecting a memory (User-in-the-Loop)."""
    
    # 1. Create a memory
    mem = LongTermMemory(
        user_id=test_user.id,
        summary_text="Inferred trait: User loves spicy food.",
        importance_score=8.5,
        confidence=0.9,
        source="inferred"
    )
    db_session.add(mem)
    await db_session.commit()
    await db_session.refresh(mem)
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        from app.api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: test_user
        
        response = await ac.post(f"/api/v1/memories/{mem.id}/reject")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    
    # 3. Verify DB State
    await db_session.refresh(mem)
    assert mem.confidence == 0.0
    assert mem.source == "rejected_by_user"
    assert mem.is_archived == True
    
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_reject_memory_not_found(db_session, test_user):
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        from app.api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: test_user
        
        response = await ac.post("/api/v1/memories/invalid-id/reject")
        
    assert response.status_code == 404
    app.dependency_overrides = {}
