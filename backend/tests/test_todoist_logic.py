import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.todoist_service import todoist_service

@pytest.fixture
def mock_httpx_response():
    def _create_response(status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            import httpx
            resp.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=resp)
        return resp
    return _create_response

@pytest.fixture
def mock_http_client():
    from infrastructure.http_client import http_client
    # Set the client to a Mock object since it is None by default
    mock_robust = MagicMock()
    mock_robust.get = AsyncMock()
    mock_robust.post = AsyncMock()
    http_client.client = mock_robust
    return mock_robust

@pytest.mark.asyncio
async def test_todoist_get_projects_cache_hit(mock_httpx_response, mock_http_client):
    # Mock Redis to return cached data
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps([{"id": "p1", "name": "Cached Project"}])
    todoist_service.redis = mock_redis
    
    projects = await todoist_service.get_projects("token", "u1")
    assert len(projects) == 1
    assert projects[0]["name"] == "Cached Project"
    mock_redis.get.assert_called_with("cache:todoist:projects:u1")

@pytest.mark.asyncio
async def test_todoist_get_projects_cache_miss(mock_httpx_response, mock_http_client):
    # Mock Redis to return None, then set cache
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    todoist_service.redis = mock_redis
    
    # Mock API
    api_resp = [{"id": "p_remote", "name": "Remote Project", "color": "red"}]
    mock_response = mock_httpx_response(200, api_resp)
    
    # Configure global mock
    mock_http_client.get.return_value = mock_response
    
    projects = await todoist_service.get_projects("real_token", "u1")
    
    assert len(projects) == 1
    assert projects[0]["id"] == "p_remote"
    
    # Verify Cache Set
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0] # key, time, value
    assert args[0] == "cache:todoist:projects:u1"
    assert args[1] == 3600
    saved_data = json.loads(args[2])
    assert saved_data[0]["id"] == "p_remote"

@pytest.mark.asyncio
async def test_todoist_sync_tasks(mock_httpx_response, mock_http_client):
    tasks = ["Buy Milk", "Long task" * 50] # Short and Long
    
    mock_response = mock_httpx_response(200, {"id": "t1"})
    mock_http_client.post.return_value = mock_response
    
    count = await todoist_service.sync_tasks_to_todoist("token", tasks, project_id="proj_1")
    
    assert count == 2
    assert mock_http_client.post.call_count == 2
    
    # Check Long Task Truncation
    # Call 2 (index 1)
    args_list = mock_http_client.post.call_args_list
    long_task_call = args_list[1]
    payload = long_task_call[1]["json"] # kwargs['json']
    
    assert len(payload["content"]) <= 250
    assert "description" in payload
    assert len(payload["description"]) > 0
    assert payload["project_id"] == "proj_1"

@pytest.mark.asyncio
async def test_todoist_sync_tasks_failure(mock_httpx_response, mock_http_client):
    tasks = ["Fail Task"]
    mock_response = mock_httpx_response(400) # API Error
    mock_http_client.post.return_value = mock_response
    
    count = await todoist_service.sync_tasks_to_todoist("token", tasks)
    
    assert count == 0 # Should fail gracefully
