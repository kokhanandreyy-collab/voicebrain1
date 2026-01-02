from typing import List, Optional, Dict, Any
import httpx
import os
import json
from loguru import logger
from app.infrastructure.config import settings
import redis.asyncio as redis
from app.infrastructure.http_client import http_client

class TodoistService:
    def __init__(self) -> None:
        self.api_url: str = "https://api.todoist.com/rest/v2"
        self.redis: redis.Redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def get_projects(self, access_token: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetches user projects from Todoist with 60m Redis caching.
        """
        cache_key = f"cache:todoist:projects:{user_id}"
        
        # 1. Check Cache
        try:
            cached_data: Optional[str] = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis error in TodoistService: {e}")

        # 2. Fetch from API
        if not access_token or access_token.startswith("mock_"):
            return [{"id": "mock_inbox", "name": "Inbox"}]

        try:
            response: httpx.Response = await http_client.client.get(
                f"{self.api_url}/projects",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            response.raise_for_status()
            
            projects: List[Dict[str, Any]] = response.json()
            # Store only necessary info: ID and Name
            project_list: List[Dict[str, Any]] = [{"id": p["id"], "name": p["name"]} for p in projects]
            
            # Cache for 60 minutes (3600s)
            await self.redis.setex(cache_key, 3600, json.dumps(project_list))
            return project_list
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Todoist API Error ({e.response.status_code}): {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Todoist Request Error: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch Todoist projects: {e}")
            
        return []

    async def sync_tasks_to_todoist(self, access_token: str, tasks: List[str], project_id: Optional[str] = None, priority: int = 1) -> int:
        """
        Syncs a list of tasks to Todoist.
        """
        if not access_token or access_token.startswith("mock_"):
            logger.info(f"[Mock Todoist] Would create tasks: {tasks} in project {project_id} with priority {priority}")
            return len(tasks)

        created_count: int = 0
        for task_content in tasks:
                try:
                    # Truncate title to 250 chars, move rest to description
                    title: str = task_content
                    description: str = ""
                    if len(title) > 250:
                        description = title[250:]
                        title = title[:250]
                        
                    payload: Dict[str, Any] = {"content": title}
                    if description:
                        payload["description"] = description
                    if project_id:
                        payload["project_id"] = project_id
                    if priority:
                        payload["priority"] = priority

                    response: httpx.Response = await http_client.client.post(
                        f"{self.api_url}/tasks",
                        json=payload,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    response.raise_for_status()
                    created_count += 1
                except httpx.HTTPStatusError as e:
                    logger.error(f"Todoist Task Creation API Error ({e.response.status_code}): {e.response.text}")
                except httpx.RequestError as e:
                    logger.error(f"Todoist Task Creation Request Error: {e}")
                except Exception as e:
                    logger.error(f"Unexpected Todoist error creating task: {e}")
        
        return created_count

todoist_service = TodoistService()
