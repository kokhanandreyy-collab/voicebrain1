import httpx
import json
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.future import select
from datetime import datetime

from app.infrastructure.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token
from app.infrastructure.database import AsyncSessionLocal

class ReadwiseService:
    def __init__(self):
        self.api_url = "https://readwise.io/api/v2/highlights/"
        self.api_key = settings.READWISE_API_KEY

    async def connect(self, user_id: str, access_token: str) -> str:
        """Store Readwise access token."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "readwise"))
            existing = result.scalars().first()
            if not existing:
                existing = Integration(user_id=user_id, provider="readwise", access_token="legacy")
                db.add(existing)
            existing.readwise_token = encrypt_token(access_token)
            await db.commit()
        return "Connected to Readwise"

    async def extract_highlight(self, voice_text: str) -> str:
        """Extract a meaningful quote/highlight from voice text via DeepSeek."""
        prompt = (
            "Extract a concise and meaningful highlight or quote from this text. "
            "If it contains several ideas, pick the most profound one. "
            "Return only the text of the highlight, no preamble."
        )
        result = await ai_service.ask_notes(voice_text, prompt)
        return result.strip()

    async def create_or_update_highlight(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Main sync logic for Readwise."""
        # 1. Extract
        highlight_text = await self.extract_highlight(voice_text)
        
        # 2. pgvector Context Check
        async with AsyncSessionLocal() as db:
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.readwise_highlight_id != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(1)
            )
            similar_note = sim_result.scalars().first()
            
            # 3. Call External API (Mocking for now)
            highlight_id = f"hl_{note_id[:8]}"
            
            # If high similarity (logic could be more complex), we'd append or link
            # For this MVP, we create a new one but track it
            
            note_res = await db.execute(select(Note).where(Note.id == note_id))
            note = note_res.scalars().first()
            if note:
                note.readwise_highlight_id = highlight_id
                await db.commit()
                
            return highlight_id

readwise_service = ReadwiseService()
