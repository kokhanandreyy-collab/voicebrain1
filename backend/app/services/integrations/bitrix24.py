from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging

class Bitrix24Integration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Bitrix24")
        
        webhook_url = integration.settings.get('webhook_url')
        if not webhook_url:
             self.logger.warning("No Webhook URL for Bitrix24")
             return

        # Sanitize URL: ensure ends with /
        if not webhook_url.endswith('/'):
            webhook_url += '/'

        # Determine Intent
        # 1. Check if 'intent' exists dynamically (if passed via some context, but here we only have Note object)
        # 2. Check tags or AI analysis
        intent = 'task'
        
        tags_lower = [t.lower() for t in (note.tags or [])]
        crm_keywords = ['lead', 'crm', 'deal', 'client', 'sales', 'salesforce', 'hubspot', 'bitrix', 'customer']
        
        if any(k in tags_lower for k in crm_keywords):
            intent = 'crm'
            
        # Optional: Check AI Analysis JSON if available
        if note.ai_analysis and isinstance(note.ai_analysis, dict):
             if note.ai_analysis.get("category", "").lower() in ["sales", "business", "crm"]:
                 intent = 'crm'

        async with httpx.AsyncClient() as client:
            try:
                if intent == 'crm':
                    # Create Lead
                    # Method: crm.lead.add
                    # Payload: fields: { TITLE: ..., COMMENTS: ... }
                    payload = {
                        "fields": {
                            "TITLE": note.title or "New Lead from VoiceBrain",
                            "COMMENTS": f"Summary: {note.summary}\n\nTranscription: {note.transcription_text}",
                            "SOURCE_ID": "VOICEBRAIN"
                        }
                    }
                    endpoint = f"{webhook_url}crm.lead.add.json"
                    
                else:
                    # Create Task
                    # Method: tasks.task.add
                    # Payload: fields: { TITLE: ..., DESCRIPTION: ... }
                    payload = {
                        "fields": {
                            "TITLE": note.title or "New Task from VoiceBrain",
                            "DESCRIPTION": f"Summary: {note.summary}\n\nAction Items: {note.action_items}",
                            # "RESPONSIBLE_ID": 1 # Default to webhook creator usually
                        }
                    }
                    endpoint = f"{webhook_url}tasks.task.add.json"
                
                response = await client.post(endpoint, json=payload)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if "result" in res_json:
                         self.logger.info(f"Successfully created Bitrix24 {intent.upper()} ID: {res_json['result']}")
                    else:
                         self.logger.error(f"Bitrix24 Response Error: {res_json}")
                else:
                    self.logger.error(f"Bitrix24 HTTP Error: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Bitrix24 Sync Exception: {e}")
