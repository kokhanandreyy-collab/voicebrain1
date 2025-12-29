from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
import re
import datetime
from app.core.config import settings
from app.core.http_client import http_client

class AmoCRMIntegration(BaseIntegration):
    async def ensure_token_valid(self, integration: Integration, db):
        if not integration.expires_at:
             return
             
        # Check expiry (with 5 min buffer)
        now = datetime.datetime.now(datetime.timezone.utc)
        if integration.expires_at > now + datetime.timedelta(minutes=5):
            return

        # AmoCRM Refresh requires client_id/secret
        self.logger.info("Refreshing AmoCRM Token...")
        client = http_client.client
        payload = {
            "client_id": settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "refresh_token": integration.auth_refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": f"{settings.API_BASE_URL}/settings/callback/amocrm" # sometimes required
        }
        
        base_url = integration.settings.get('base_url')
        if not base_url: return

        try:
            resp = await client.post(f"{base_url}/oauth2/access_token", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                integration.auth_token = data["access_token"]
                if data.get("refresh_token"):
                    integration.auth_refresh_token = data["refresh_token"] # Rotate refresh token if provided
                
                expires_in = data.get("expires_in", 86400)
                integration.expires_at = now + datetime.timedelta(seconds=expires_in)
                
                db.add(integration)
                await db.commit()
                self.logger.info("AmoCRM Token refreshed.")
            else:
                self.logger.error(f"Failed to refresh AmoCRM token: {resp.text}")
        except Exception as e:
            self.logger.error(f"Refresh error: {e}")

    async def sync(self, integration: Integration, note: Note, db):
        await self.ensure_token_valid(integration, db)
        self.logger.info(f"Syncing note {note.id} to AmoCRM")
        
        # Check intent (Simple routing)
        intent = 'task' # default
        tags_lower = [t.lower() for t in (note.tags or [])]
        if any(k in tags_lower for k in ['lead', 'crm', 'client', 'sales', 'amocrm']):
            intent = 'crm'
            
        # Also check explicit AI analysis if available
        if note.ai_analysis and isinstance(note.ai_analysis, dict):
             if note.ai_analysis.get("category", "").lower() in ["sales", "crm"]:
                 intent = 'crm'

        # If strict requirement "ONLY if intent is crm", we return otherwise
        if intent != 'crm':
            self.logger.info("Skipping AmoCRM sync: Intent is not 'crm'")
            return

        token = integration.auth_token
        # Base URL should have been saved during OAuth callback (e.g., https://subdomain.amocrm.ru)
        base_url = integration.settings.get('base_url')
        
        if not base_url:
             self.logger.error("Configuration incomplete: base_url missing for AmoCRM")
             # Optionally raise exception if we want to fail explicitly
             return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                # 1. Create Lead
                # POST /api/v4/leads
                
                # Extract Price (simple regex for int)
                price = 0
                match = re.search(r'\d+', note.transcription_text or "")
                if match:
                    try:
                        price = int(match.group())
                    except: pass
                
                lead_payload = [
                    {
                        "name": note.title or "New Lead",
                        "price": price,
                        "pipeline_id": None, # Default
                    }
                ]
                
                lead_res = await client.post(
                    f"{base_url}/api/v4/leads",
                    headers=headers,
                    json=lead_payload
                )
                
                lead_id = None
                if lead_res.status_code in (200, 201):
                    data = lead_res.json()
                    if "_embedded" in data and "leads" in data["_embedded"]:
                        lead_id = data["_embedded"]["leads"][0]["id"]
                        self.logger.info(f"Created AmoCRM Lead ID: {lead_id}")
                elif lead_res.status_code == 204:
                     # 204 No Content means success but no body? 
                     # Actually for creating leads, AmoCRM *should* return the ID.
                     # If it returns 204, we might not have the ID to attach notes.
                     # But user requested to handle 204 as success. 
                     # If 204, we can't continue to add note/task easily without ID.
                     # We'll log it and maybe try to fetch latest lead?
                     # Or assuming the user knows AmoCRM quirks, maybe they meant "sometimes it returns 204 on update". 
                     # But for create, we need ID.
                     # Let's log success but return early as we can't attach items.
                     self.logger.info("AmoCRM returned 204 (Success) but no content. Cannot attach notes.")
                     return
                else:
                    self.logger.error(f"AmoCRM Lead Creation Failed: {lead_res.text}")
                    return

                if not lead_id:
                    return

                # 2. Add Note to Lead
                # POST /api/v4/leads/{id}/notes
                note_payload = [
                    {
                        "note_type": "common",
                        "params": {
                            "text": f"Summary: {note.summary}\n\nTranscript: {note.transcription_text}"
                        }
                    }
                ]
                await client.post(
                     f"{base_url}/api/v4/leads/{lead_id}/notes",
                     headers=headers,
                     json=note_payload
                )

                # 3. Add Task to Lead
                # POST /api/v4/tasks
                task_payload = [
                    {
                        "text": "Processed from VoiceBrain",
                        "complete_till": int(note.created_at.timestamp() + 86400), # Tomorrow
                        "entity_id": lead_id,
                        "entity_type": "leads"
                    }
                ]
                await client.post(
                     f"{base_url}/api/v4/tasks",
                     headers=headers,
                     json=task_payload
                )
                    
            except Exception as e:
                self.logger.error(f"AmoCRM Sync Exception: {e}")
