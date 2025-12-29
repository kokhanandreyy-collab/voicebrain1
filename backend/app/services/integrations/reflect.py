from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
from datetime import datetime

class ReflectIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Reflect")
        
        # 1. Authenticate
        # Reflect usually requires an Access Token and a Graph ID.
        # We assume integration.access_token stores the API Key.
        # We assume integration.settings['graph_id'] stores the Graph ID.
        
        access_token = integration.access_token
        if isinstance(access_token, dict):
            access_token = access_token.get("access_token") 
        
        if not access_token:
            raise ValueError("Reflect API Token missing")
            
        graph_id = (integration.settings or {}).get("graph_id")
        if not graph_id:
             raise ValueError("Reflect Graph ID missing in settings")
             
        # 2. Format Content (Markdown)
        # Header
        content = f"## 🎙️ Voice Note: {note.title or 'Untitled'}\n\n"
        
        # Summary
        if note.summary:
            safe_summary = self.sanitize_text(note.summary)
            content += f"### Summary\n{safe_summary}\n\n"
            
        # Action Items
        if note.action_items:
            content += "### Action Items\n"
            for item in note.action_items:
                content += f"- [ ] {item}\n"
            content += "\n"
            
        # Link back
        # content += f"[View in VoiceBrain](https://voicebrain.app/notes/{note.id})\n\n"
        
        # Transcript (Collapsible if Reflect supports it, typically indentation or details tag works in some MD)
        # Reflect supports standard MD.
        if note.transcription_text:
             safe_transcript = self.sanitize_text(note.transcription_text)
             content += f"### Transcript\n{safe_transcript[:5000]}...\n" # Truncate if too long
             
        # 3. Send Request
        # API Endpoint: POST https://api.reflect.app/v1/graphs/{graphId}/daily-notes
        # Date: Today (ISO YYYY-MM-DD or specific to Reflect)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        body = {
            "date": date_str,
            "text": content,
            "transform_type": "append" # Hypothetical param, usually just posting appends
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Using the standard Append to Daily Note endpoint structure
                res = await client.post(
                    f"https://api.reflect.app/v1/graphs/{graph_id}/daily-notes",
                    headers=headers,
                    json=body
                )
                res.raise_for_status()
                self.logger.info(f"Appended note to Reflect Daily Note for {date_str}")
            except Exception as e:
                self.logger.error(f"Reflect sync failed: {e}")
                raise e
