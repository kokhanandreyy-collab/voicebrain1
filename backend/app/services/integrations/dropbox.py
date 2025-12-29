from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
import json
import datetime

class DropboxIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Dropbox")
        
        # Dropbox API requires the token
        token = integration.access_token
        
        # Prepare Markdown Content
        title = note.title or "Untitled Note"
        date_str = note.created_at.strftime('%Y-%m-%d %H:%M') if note.created_at else "Unknown Date"
        
        md_content = f"# {title}\n\n"
        md_content += f"**Date:** {date_str}\n\n"
        
        if note.tags:
            md_content += f"**Tags:** {', '.join(note.tags)}\n\n"
            
        md_content += f"## Summary\n{self.sanitize_text(note.summary) or 'No summary available.'}\n\n"
        
        if note.action_items:
            md_content += "## Action Items\n"
            for item in note.action_items:
                md_content += f"- [ ] {item}\n"
            md_content += "\n"
            
        md_content += f"## Transcript\n{self.sanitize_text(note.transcription_text) or '(No transcription available)'}\n"
        
        # Dropbox API Args
        # Path must start with /
        # Use shared filename sanitization
        safe_title = self.sanitize_filename(title)
        path = f"/VoiceBrain/{safe_title}.md"
        
        api_args = {
            "path": path,
            "mode": "add",
            "autorename": True, # Automatically handle collisions by appending (1), (2) etc.
            "mute": False,
            "strict_conflict": False
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps(api_args),
            "Content-Type": "application/octet-stream"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://content.dropboxapi.com/2/files/upload",
                    headers=headers,
                    content=md_content.encode('utf-8')
                )
                
                if response.status_code == 200:
                    res_json = response.json()
                    self.logger.info(f"Successfully uploaded to Dropbox: {res_json.get('path_display')}")
                else:
                    self.logger.error(f"Dropbox API Error ({response.status_code}): {response.text}")
                    raise Exception(f"Dropbox Upload Failed: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Dropbox Sync Exception: {e}")
                raise e
