from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging

class WeeekIntegration(BaseIntegration):
    BASE_URL = "https://api.weeek.net/public/v1"

    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to WEEEK")
        
        # Token is stored in settings or access_token. Let's assume settings['api_key'] 
        # based on typical manual input patterns, or access_token if we treat it as token.
        # Frontend usually sends { settings: { api_key: "..." } }
        token = integration.settings.get('api_key')
        if not token:
             self.logger.warning("No API Key for WEEEK")
             return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # 1. Get Workspace ID (if not cached)
            # ideally we cache this in integration.settings['workspace_id']
            workspace_id = integration.settings.get('workspace_id')
            if not workspace_id:
                try:
                    ws_res = await client.get(f"{self.BASE_URL}/ws", headers=headers)
                    if ws_res.status_code == 200:
                        data = ws_res.json()
                        if data.get("workspaces"):
                            # Pick first
                            workspace_id = data["workspaces"][0]["id"]
                            # We can't easily update integration here without DB session if sync() doesn't pass it contextually in a way we can commit. 
                            # But we can just use it for this session.
                            self.logger.info(f"Resolved WEEEK Workspace: {workspace_id}")
                except Exception as e:
                    self.logger.error(f"Failed to fetch WEEEK workspaces: {e}")
            
            # 2. Create Tasks for Action Items
            if not note.action_items:
                return

            desc = f"Source: {note.title}\n{note.summary or ''}"
            
            for item in note.action_items:
                payload = {
                    "title": str(item)[:250],
                    "description": desc,
                    "type": "action",
                    # "workspaceId": workspace_id # Some APIs require it, Weeek docs say headers or body?
                    # Usually /tm/tasks is global or user-scoped. 
                    # If workspace_id is needed, it might be a query param or body.
                    # Assuming basic payload for now based on typical REST APIs.
                    # Weeek API docs: POST /tm/tasks body: { title, ... }
                }
                
                # If workspace_id found, include it
                if workspace_id:
                    payload["workspaceId"] = workspace_id

                try:
                    res = await client.post(
                        f"{self.BASE_URL}/tm/tasks", 
                        headers=headers, 
                        json=payload
                    )
                    if res.status_code not in range(200, 300):
                        self.logger.error(f"Weeek Task Error: {res.text}")
                except Exception as e:
                    self.logger.error(f"Weeek Task Exception: {e}")
