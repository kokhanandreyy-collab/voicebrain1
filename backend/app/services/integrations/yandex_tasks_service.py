import httpx
import json
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.future import select
from datetime import datetime

from infrastructure.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token, decrypt_token
from infrastructure.database import AsyncSessionLocal

class YandexTasksService:
    def __init__(self):
        self.client_id = settings.YANDEX_TASKS_CLIENT_ID
        self.client_secret = settings.YANDEX_TASKS_CLIENT_SECRET
        self.token_url = "https://oauth.yandex.ru/token"
        self.api_base_url = "https://api.tracker.yandex.net/v2" # Note: Yandex uses Tracker for Tasks/Issues in many cases, or specialized Tasks API. Assuming Tracker API for advanced task management.

    async def connect(self, user_id: str, code: str) -> str:
        """Connect Yandex account via OAuth."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"Yandex Tasks OAuth Failed: {resp.text}")
                raise Exception("Failed to connect Yandex Tasks")
            
            data = resp.json()
            access_token = data.get("access_token")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "yandex_tasks"))
                existing = result.scalars().first()
                if not existing:
                    existing = Integration(user_id=user_id, provider="yandex_tasks", access_token="legacy")
                    db.add(existing)
                existing.yandex_tasks_token = encrypt_token(access_token)
                await db.commit()
        return "Connected to Yandex Tasks"

    async def extract_task_details(self, voice_text: str) -> Dict[str, Any]:
        """Extract task details via DeepSeek."""
        prompt = (
            "Extract task details from this text in JSON format: "
            "{ 'summary': string, 'description': string, 'due_date': ISO8601 string or null, 'recurring': string or null }. "
            "Example recurring: 'daily', 'weekly on friday'."
        )
        result = await ai_service.ask_notes(voice_text, prompt)
        try:
            clean_json = result.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception:
            return {"summary": voice_text[:50], "description": voice_text, "due_date": None, "recurring": None}

    async def create_or_update_task(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Main sync logic: extract -> context search -> api call."""
        # 1. Extract Details
        details = await self.extract_task_details(voice_text)
        
        # 2. Context Aware RAG
        async with AsyncSessionLocal() as db:
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.yandex_task_id != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(1)
            )
            similar_note = sim_result.scalars().first()
            
            # 3. Call External API (Mocking)
            task_id = f"yandex_task_{note_id[:8]}"
            
            note_res = await db.execute(select(Note).where(Note.id == note_id))
            note = note_res.scalars().first()
            if note:
                note.yandex_task_id = task_id
                await db.commit()
                
            return task_id

yandex_tasks_service = YandexTasksService()
