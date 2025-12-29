from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import urllib.parse

class VKIntegration(BaseIntegration):
    API_VERSION = "5.131"
    
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to VK")
        
        token = integration.access_token
        if not token:
             self.logger.warning("Missing Access Token for VK")
             return

        # Prepare Message
        # Title usually bold or separate line
        clean_transcript = self.sanitize_text(note.transcription_text or note.summary)
        message = f"{note.title or 'New Voice Note'}\n\n{clean_transcript}"
        
        # Add hashtags
        if note.tags:
            tags_str = " ".join([f"#{t.replace(' ', '_')}" for t in note.tags])
            message += f"\n\n{tags_str}"
            
        # Add footer
        message += "\n\n(Sent via VoiceBrain)"

        # Truncate to 4000 chars for VK API safety
        if len(message) > 4000:
            suffix = "\n\n... (Read more in dashboard)"
            message = message[:4000 - len(suffix)] + suffix

        async with httpx.AsyncClient() as client:
            try:
                # POST /method/wall.post
                # params: access_token, v, message
                
                params = {
                    "access_token": token,
                    "v": self.API_VERSION,
                    "message": message,
                    # "owner_id": user_id (if we stored it, implies current user if omitted usually? No, implied is current user context)
                }
                
                res = await client.post(
                    "https://api.vk.com/method/wall.post",
                    data=params # VK API accepts query params or form data
                )
                
                data = res.json()
                
                if "error" in data:
                    self.logger.error(f"VK Sync Error: {data['error']}")
                else:
                    post_id = data.get('response', {}).get('post_id')
                    self.logger.info(f"Created VK Post ID: {post_id}")

            except Exception as e:
                self.logger.error(f"VK Sync Exception: {e}")
