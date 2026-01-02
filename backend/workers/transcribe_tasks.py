from typing import Tuple, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.models import Note, User
from app.infrastructure.database import AsyncSessionLocal
from app.core.audio import audio_processor

# Kept steps here or use audio processor?
# If I remove steps here, I might break imports in pipeline IF pipeline was importing from here.
# But I refactored pipeline to use audio.py.
# So I can strip this file to be just a wrapper.

async def _process_transcribe_async(note_id: str) -> None:
    from app.services.pipeline import pipeline
    await pipeline.process(note_id)

@celery.task(name="transcribe.process_note")
def process_transcribe(note_id: str):
    async_to_sync(_process_transcribe_async)(note_id)
    return {"status": "processing_started", "note_id": note_id}
