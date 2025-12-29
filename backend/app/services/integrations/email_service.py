import httpx
import json
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.future import select

from app.core.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token
from app.core.database import AsyncSessionLocal

class EmailService:
    def __init__(self):
        self.gmail_client_id = settings.GMAIL_CLIENT_ID
        self.gmail_client_secret = settings.GMAIL_CLIENT_SECRET
        self.outlook_client_id = settings.OUTLOOK_CLIENT_ID
        self.outlook_client_secret = settings.OUTLOOK_CLIENT_SECRET

    async def connect_gmail(self, user_id: str, code: str) -> str:
        """Connect Gmail account via OAuth."""
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": self.gmail_client_id,
            "client_secret": self.gmail_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{settings.API_BASE_URL}/api/v1/integrations/gmail/callback"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"Gmail OAuth Failed: {resp.text}")
                raise Exception("Failed to connect Gmail")
            data = resp.json()
            access_token = data.get("access_token")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "gmail"))
                existing = result.scalars().first()
                if not existing:
                    existing = Integration(user_id=user_id, provider="gmail", access_token="legacy")
                    db.add(existing)
                existing.gmail_token = encrypt_token(access_token)
                await db.commit()
        return "Connected to Gmail"

    async def connect_outlook(self, user_id: str, code: str) -> str:
        """Connect Outlook account via OAuth."""
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        payload = {
            "client_id": self.outlook_client_id,
            "client_secret": self.outlook_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{settings.API_BASE_URL}/api/v1/integrations/outlook/callback"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"Outlook OAuth Failed: {resp.text}")
                raise Exception("Failed to connect Outlook")
            data = resp.json()
            access_token = data.get("access_token")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "outlook"))
                existing = result.scalars().first()
                if not existing:
                    existing = Integration(user_id=user_id, provider="outlook", access_token="legacy")
                    db.add(existing)
                existing.outlook_token = encrypt_token(access_token)
                await db.commit()
        return "Connected to Outlook"

    async def create_or_update_draft(self, user_id: str, note_id: str, voice_text: str, provider: str = "gmail") -> str:
        """Generate subject/body and create/update draft."""
        # 1. Generate Email Content
        prompt = (
            "Generate an email draft based on this voice note. "
            "Return JSON: { 'subject': string, 'body': string }. "
            "The tone should be professional but conversational."
        )
        result = await ai_service.ask_notes(voice_text, prompt)
        try:
            clean_json = result.strip().replace("```json", "").replace("```", "").strip()
            content = json.loads(clean_json)
        except Exception:
            content = {"subject": "Note from VoiceBrain", "body": voice_text}

        # 2. pgvector Context Check (RAG)
        async with AsyncSessionLocal() as db:
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.email_draft_id != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(1)
            )
            similar_note = sim_result.scalars().first()
            
            # If high similarity, we could append. For now, we create new draft.
            # 3. Create Draft (Mocking API Call)
            draft_id = f"draft_{provider}_{note_id[:8]}"
            
            note_res = await db.execute(select(Note).where(Note.id == note_id))
            note = note_res.scalars().first()
            if note:
                note.email_draft_id = draft_id
                await db.commit()
                
        return draft_id

email_service = EmailService()
