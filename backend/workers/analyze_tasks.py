from typing import Dict, Any, List, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User, NoteEmbedding
from infrastructure.database import AsyncSessionLocal
from app.core.types import AIAnalysisPack

async def _process_analyze_async(note_id: str) -> None:
    from app.services.pipeline import pipeline
    await pipeline.process(note_id)

@celery.task(name="analyze.process_note")
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "analysis_restarted", "note_id": note_id}
