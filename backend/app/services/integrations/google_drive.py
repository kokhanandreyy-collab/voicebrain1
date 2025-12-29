from .base import BaseIntegration
from app.models import Integration, Note
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import UserCreds
import logging
import json
import datetime
from app.core.config import settings
from app.core.http_client import http_client

class GoogleDriveIntegration(BaseIntegration):
    async def ensure_token_valid(self, integration: Integration, db):
        if not integration.expires_at:
             return
             
        # Check expiry (with 5 min buffer)
        now = datetime.datetime.now(datetime.timezone.utc)
        if integration.expires_at > now + datetime.timedelta(minutes=5):
            return

        if not integration.refresh_token:
            self.logger.warning("Token expired but no refresh token.")
            return

        self.logger.info("Refreshing Google Drive Token...")
        client = http_client.client
        payload = {
            "client_id": settings.GOOGLE_DRIVE_CLIENT_ID or settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET or settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": integration.refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            resp = await client.post("https://oauth2.googleapis.com/token", data=payload)
            if resp.status_code == 200:
                data = resp.json()
                integration.access_token = data["access_token"]
                # Update expiry
                expires_in = data.get("expires_in", 3600)
                integration.expires_at = now + datetime.timedelta(seconds=expires_in)
                
                # Save to DB
                db.add(integration)
                await db.commit()
                
                self.logger.info("Token refreshed successfully.")
            else:
                self.logger.error(f"Failed to refresh token: {resp.text}")
        except Exception as e:
            self.logger.error(f"Refresh error: {e}")

    async def sync(self, integration: Integration, note: Note, db):
        await self.ensure_token_valid(integration, db)
        self.logger.info(f"Syncing note {note.id} to Google Drive")
        
        for attempt in range(2):
            try:
                user_creds = {
                    "access_token": integration.access_token,
                    "token_type": "Bearer",
                    "expires_in": 3600, 
                }
                
                async with Aiogoogle(user_creds=user_creds) as aiogoogle:
                    drive_v3 = await aiogoogle.discover('drive', 'v3')
                    
                    # 1. Find or Create Folder
                    folder_name = "VoiceBrain Notes"
                    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
                    
                    response = await aiogoogle.as_user(aiogoogle.service_key).drive.files.list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)'
                    )
                    files = response.get('files', [])
                    
                    if files:
                        folder_id = files[0]['id']
                    else:
                        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                        folder = await aiogoogle.as_user(aiogoogle.service_key).drive.files.create(json=file_metadata, fields='id')
                        folder_id = folder.get('id')

                    # 2. Prepare Content (with sanitization)
                    safe_title = self.sanitize_text(note.title or "Untitled")
                    content = f"Title: {safe_title}\n"
                    if note.created_at:
                        content += f"Date: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    content += f"\nSummary:\n{self.sanitize_text(note.summary or '')}\n"
                    
                    if note.action_items:
                        content += "\nAction Items:\n"
                        for item in note.action_items:
                            content += f"- {item}\n"
                    
                    content += f"\nTranscript:\n{self.sanitize_text(note.transcription_text or '')}\n"

                    # 3. Upload File
                    import io
                    from aiogoogle.models import MediaUpload
                    
                    file_metadata = {
                        'name': safe_title,
                        'parents': [folder_id],
                        'mimeType': 'application/vnd.google-apps.document'
                    }
                    
                    media_stream = io.StringIO(content)
                    media_upload = MediaUpload(media_stream, mimetype='text/plain')
                    
                    uploaded_file = await aiogoogle.as_user(aiogoogle.service_key).drive.files.create(
                        json=file_metadata,
                        media_upload=media_upload,
                        fields='id'
                    )
                    
                    self.logger.info(f"Created Google Doc with ID {uploaded_file.get('id')}")
                    return

            except Exception as e:
                # Handle 401 Unauthorized
                if "401" in str(e) or "unauthorized" in str(e).lower():
                    if attempt == 0:
                        self.logger.info("Google token might be expired. Refreshing...")
                        await self.ensure_token_valid(integration, db)
                        continue
                
                self.logger.error(f"Google Drive sync failed (Attempt {attempt+1}): {e}")
                if attempt == 1:
                    raise e
