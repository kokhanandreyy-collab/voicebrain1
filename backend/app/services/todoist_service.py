import httpx
import os
import json
import logging
from app.core.config import settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class TodoistService:
    def __init__(self):
        self.api_url = "https://api.todoist.com/rest/v2"
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def get_projects(self, access_token: str, user_id: str) -> list[dict]:
        """
        Fetches user projects from Todoist with 60m Redis caching.
        """
        cache_key = f"cache:todoist:projects:{user_id}"
        
        # 1. Check Cache
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis error in TodoistService: {e}")

        # 2. Fetch from API
        if not access_token or access_token.startswith("mock_"):
            return [{"id": "mock_inbox", "name": "Inbox"}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    projects = response.json()
                    # Store only necessary info: ID and Name
                    project_list = [{"id": p["id"], "name": p["name"]} for p in projects]
                    
                    # Cache for 60 minutes (3600s)
                    await self.redis.setex(cache_key, 3600, json.dumps(project_list))
                    return project_list
        except Exception as e:
            logger.error(f"Failed to fetch Todoist projects: {e}")
            
        return []

    async def sync_tasks_to_todoist(self, access_token: str, tasks: list[str], project_id: str = None, priority: int = 1) -> int:
        """
        Syncs a list of tasks to Todoist.
        """
        if not access_token or access_token.startswith("mock_"):
            print(f"[Mock Todoist] Would create tasks: {tasks} in project {project_id} with priority {priority}")
            return len(tasks)

        created_count = 0
        async with httpx.AsyncClient() as client:
            for task_content in tasks:
                try:
                    # Truncate title to 250 chars, move rest to description
                    title = task_content
                    description = ""
                    if len(title) > 250:
                        description = title[250:]
                        title = title[:250]
                        
                    payload = {"content": title}
                    if description:
                        payload["description"] = description
                    if project_id:
                        payload["project_id"] = project_id
                    if priority:
                        payload["priority"] = priority

                    response = await client.post(
                        f"{self.api_url}/tasks",
                        json=payload,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if response.status_code == 200:
                        created_count += 1
                    else:
                        print(f"[Todoist Error] Failed to create task '{task_content}': {response.text}")
                except Exception as e:
                    print(f"[Todoist Exception] {e}")
        
        return created_count

todoist_service = TodoistService()
