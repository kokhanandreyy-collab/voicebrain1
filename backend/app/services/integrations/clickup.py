from .base import BaseIntegration
from app.models import Integration, Note
from app.core.http_client import http_client
import logging
import json

class ClickUpIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to ClickUp")
        
        token = integration.access_token
        list_id = (integration.settings or {}).get("list_id")
        
        if not list_id:
             self.logger.warning("No List ID configured for ClickUp integration.")
             raise ValueError("ClickUp List ID not configured. Please select a list in settings.")

        if not note.action_items:
            self.logger.info("No action items to sync to ClickUp.")
            return

        headers = {
            "Authorization": token, # ClickUp uses pure token, sometimes Bearer depending on OAuth vs PK. OAuth is usually Bearer.
            # However, ClickUp API docs say "Authorization: {token}". Let's assume standard OAuth Bearer unless specified otherwise.
            # Confirmed: Standard OAuth uses Bearer, Personal Token uses just string.
            # Safe bet is typically "Bearer {token}" for OAuth2.
             "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        client = http_client.client
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
        
        for item in note.action_items:
            # Truncate title
            safe_title = str(item)[:250]
            
            payload = {
                "name": safe_title,
                "description": f"{note.summary or ''}\n\nView Note: https://voicebrain.app/notes/{note.id}",
                "status": "OPEN", # Default status, optional
                "notify_all": False
            }

            try:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"Created ClickUp Task: {data.get('id')} ({data.get('name')})")
                else:
                    self.logger.error(f"ClickUp API Error ({response.status_code}): {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Failed to create ClickUp task for '{item}': {e}")
                # Continue to next item
