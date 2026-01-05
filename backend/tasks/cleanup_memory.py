from datetime import datetime, timedelta, timezone
from celery import shared_task
from sqlalchemy import delete
from app.models import Note, LongTermMemory
from infrastructure.database import AsyncSessionLocal as async_session
from loguru import logger
import asyncio

async def run_cleanup_async():
    async with async_session() as session:
        try:
            # Use timezone-aware UTC for consistency
            now = datetime.now(timezone.utc)
            ninety_days_ago = now - timedelta(days=90)
            one_eighty_days_ago = now - timedelta(days=180)

            # Удалить Note с score <4 старше 90 дней
            deleted_notes = await session.execute(
                delete(Note).where(
                    Note.importance_score < 4,
                    Note.created_at < ninety_days_ago
                )
            )

            # Удалить LongTermMemory с score <5 старше 180 дней
            deleted_longterm = await session.execute(
                delete(LongTermMemory).where(
                    LongTermMemory.importance_score < 5,
                    LongTermMemory.created_at < one_eighty_days_ago
                )
            )

            await session.commit()
            logger.info(f"Cleanup completed: deleted {deleted_notes.rowcount} notes and {deleted_longterm.rowcount} longterm memories")
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            await session.rollback()

@shared_task(name="cleanup_memory")
def cleanup_memory():
    asyncio.run(run_cleanup_async())
