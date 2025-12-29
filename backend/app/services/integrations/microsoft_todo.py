from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
from app.core.config import settings

class MicrosoftTodoIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Microsoft To Do")
        
        if not note.action_items:
            self.logger.info("No action items to sync.")
            return

        # 1. Authenticate
        # Assuming integration.access_token is the Bearer token string or a dict containing it.
        # We usually store the full token response.
        access_token = integration.access_token
        if isinstance(access_token, dict):
            access_token = access_token.get("access_token")
            
        if not access_token:
            raise ValueError("Microsoft To Do access token missing")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # 2. Get List ID
            list_id = (integration.settings or {}).get("list_id")
            
            if not list_id:
                # Fetch default list
                try:
                    res = await client.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers)
                    res.raise_for_status()
                    lists = res.json().get("value", [])
                    
                    # Find default "Tasks" list or just the first one
                    default_list = next((l for l in lists if l.get("displayName") == "Tasks" or l.get("isDefaultFolder")), lists[0] if lists else None)
                    
                    if default_list:
                        list_id = default_list["id"]
                        self.logger.info(f"Using default task list: {default_list.get('displayName')}")
                    else:
                        raise ValueError("No To Do lists found.")
                        
                except Exception as e:
                    self.logger.error(f"Failed to fetch default list: {e}")
                    raise e
            
            # 3. Create Tasks
            base_url = "https://voicebrain.app" # MVP hardcode or fetch from settings
            
            for item in note.action_items:
                try:
                    # Determine Importance
                    importance = "normal"
                    if note.tags and any(t.lower() in ["urgent", "high priority", "critical"] for t in note.tags):
                        importance = "high"
                    
                    # Truncate Title
                    title_str = str(item)
                    safe_title = title_str[:250] if len(title_str) > 250 else title_str

                    # Prepare Task
                    body = {
                        "title": safe_title,
                        "importance": importance,
                        "body": {
                            "content": f"{note.summary or ''}\n\nView Note: {base_url}/dashboard/notes/{note.id}",
                            "contentType": "text"
                        }
                    }
                    
                    post_res = await client.post(
                        f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks",
                        headers=headers,
                        json=body
                    )
                    post_res.raise_for_status()
                    self.logger.info(f"Created MS To Do task: {item[:20]}...")
                    
                except Exception as task_err:
                    self.logger.error(f"Failed to create task '{item}': {task_err}")
                    # Continue to next item
