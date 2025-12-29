from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging

class KaitenIntegration(BaseIntegration):
    BASE_URL = "https://kaiten.ru/api/latest"

    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Kaiten")
        
        token = integration.settings.get('api_key')
        board_id = integration.settings.get('board_id')
        
        if not token or not board_id:
             self.logger.warning("Missing Token or Board ID for Kaiten")
             return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                # Create Card
                # Endpoint: POST /cards (v1) or /api/latest/cards
                # Payload requires boardId, title.
                # Description can be html or text.
                
                payload = {
                    "boardId": int(board_id),
                    "title": (note.title or "New Note")[:250],
                    "description": f"<p>{note.summary}</p><br><p><strong>Transcript:</strong><br>{note.transcription_text}</p>",
                    "properties": {
                         # Optional: Add priority if mapped
                    }
                }
                
                # Check for priority
                # Note priority 1-4. Kaiten service class? Or tags?
                # Keeping it simple for MVP.
                
                res = await client.post(
                    f"{self.BASE_URL}/cards",
                    headers=headers,
                    json=payload
                )
                
                if res.status_code in (200, 201):
                    card = res.json()
                    self.logger.info(f"Created Kaiten Card ID: {card.get('id')}")
                else:
                    self.logger.error(f"Kaiten Sync Error: {res.text}")

            except Exception as e:
                self.logger.error(f"Kaiten Sync Exception: {e}")
