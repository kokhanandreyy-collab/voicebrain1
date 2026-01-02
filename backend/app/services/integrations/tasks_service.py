import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.future import select

from infrastructure.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token, decrypt_token
from infrastructure.database import AsyncSessionLocal

class TasksService:
    def __init__(self):
        self.apple_client_id = settings.APPLE_CLIENT_ID
        self.apple_client_secret = settings.APPLE_CLIENT_SECRET
        self.google_tasks_client_id = settings.GOOGLE_TASKS_CLIENT_ID
        self.google_tasks_client_secret = settings.GOOGLE_TASKS_CLIENT_SECRET

    async def connect_apple(self, user_id: str, code: str) -> str:
        """Connect Apple account (OAuth flow placeholder)."""
        # Apple OAuth is complex (JWT based). This is a placeholder for the flow.
        logger.info(f"Connecting Apple Reminders for user {user_id}")
        # In a real app, we'd exchange the code for a token here.
        access_token = f"apple_token_{code}"
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "apple_reminders"))
            existing = result.scalars().first()
            if not existing:
                existing = Integration(user_id=user_id, provider="apple_reminders", access_token="legacy")
                db.add(existing)
            existing.apple_reminders_token = encrypt_token(access_token)
            await db.commit()
        return "Connected to Apple Reminders"

    async def connect_google_tasks(self, user_id: str, code: str) -> str:
        """Connect Google account for Tasks."""
        logger.info(f"Connecting Google Tasks for user {user_id}")
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": self.google_tasks_client_id,
            "client_secret": self.google_tasks_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{settings.API_BASE_URL}/api/v1/integrations/google-tasks/callback"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"Google Tasks OAuth Failed: {resp.text}")
                raise Exception("Failed to connect Google Tasks")
            
            access_token = resp.json().get("access_token")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "google_tasks"))
                existing = result.scalars().first()
                if not existing:
                    existing = Integration(user_id=user_id, provider="google_tasks", access_token="legacy")
                    db.add(existing)
                existing.google_tasks_token = encrypt_token(access_token)
                await db.commit()
        return "Connected to Google Tasks"

    async def extract_task_details(self, voice_text: str) -> Dict[str, Any]:
        """Extract task details via DeepSeek."""
        prompt = (
            "Extract task details from this text in JSON format: "
            "{ 'title': string, 'due_date': ISO8601 string or null, 'recurring': string or null, 'note': string }. "
            "If it's a reminder to do something, extract the intent. "
            "Example recurring: 'Every Monday', 'Daily'."
        )
        import json
        result = await ai_service.ask_notes(voice_text, prompt)
        try:
            # Simple cleanup if AI adds markdown blocks
            clean_json = result.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception:
            return {"title": voice_text[:50], "due_date": None, "recurring": None, "note": voice_text}

    async def create_or_update_reminder(self, user_id: str, note_id: str, voice_text: str, provider: str = "google_tasks") -> str:
        """Main sync logic: extract -> context search -> api call."""
        # 1. Extract
        details = await self.extract_task_details(voice_text)
        
        # 2. Context Aware RAG
        # Search for similar existing reminders to avoid duplicates
        async with AsyncSessionLocal() as db:
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.reminder_id != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(3)
            )
            similar_notes = sim_result.scalars().all()
            
            # If we decided to append, we would find the existing reminder_id here.
            # For simplicity, we create a new one, but if similarity is very high (>0.8), we could log/notify.
            
            note_res = await db.execute(select(Note).where(Note.id == note_id))
            note = note_res.scalars().first()
            if not note: return "Note not found"

            # 3. Call External API (Mocking for now as per user pattern)
            task_id = f"task_{provider}_{datetime.now().timestamp()}"
            
            # Save to database
            note.reminder_id = task_id
            await db.commit()
            
            return f"Created {provider} reminder: {task_id}"

tasks_service = TasksService()
