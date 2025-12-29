from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
import json
import datetime

class YandexDiskIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Yandex Disk")
        
        token = integration.access_token
        if not token:
             self.logger.warning("No access token for Yandex Disk")
             return

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

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"OAuth {token}"}
            
            # 1. Ensure Folder exists
            try:
                # "201 Created" if created, "409 Conflict" if exists (which is fine)
                await client.put(
                    "https://cloud-api.yandex.net/v1/disk/resources?path=VoiceBrain",
                    headers=headers
                )
            except Exception:
                pass # Ignore if exists

            # 2. Get Upload Link
            # Use shared filename sanitization
            safe_title = self.sanitize_filename(title)
            path = f"VoiceBrain/{safe_title}.md"
            
            # overwrite=false to prevent errors on frequent updates (avoiding accidental data loss)
            upload_url_res = await client.get(
                f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={path}&overwrite=false",
                headers=headers
            )
            
            if upload_url_res.status_code != 200:
                self.logger.error(f"Failed to get upload link: {upload_url_res.text}")
                raise Exception(f"Yandex Upload Init Failed: {upload_url_res.text}")
                
            href = upload_url_res.json().get("href")
            
            # 3. Upload File
            upload_res = await client.put(
                href,
                content=md_content.encode('utf-8')
            )
            
            if upload_res.status_code in (201, 202, 200):
                 self.logger.info(f"Successfully uploaded to Yandex Disk: {path}")
            else:
                 self.logger.error(f"Yandex File Upload Failed: {upload_res.text}")
                 raise Exception(f"Yandex Upload Failed: {upload_res.text}")
