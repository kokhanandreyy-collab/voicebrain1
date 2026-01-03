from datetime import datetime, timedelta, timezone
from celery import shared_task
from sqlalchemy import delete
from loguru import logger
import asyncio

# Using absolute paths as per project structure
from app.models import Note, LongTermMemory
from infrastructure.database import AsyncSessionLocal as async_session

@shared_task(name="cleanup_memory")
def cleanup_memory():
    async def run_cleanup():
        # Using context manager for safe session handling
        async with async_session() as session:
            try:
                # Use timezone-aware UTC for consistency
                now = datetime.now(timezone.utc)
                ninety_days_ago = now - timedelta(days=90)
                one_eighty_days_ago = now - timedelta(days=180)

                # 1. Delete Note with score < 4 older than 90 days
                deleted_notes_res = await session.execute(
                    delete(Note).where(
                        Note.importance_score < 4,
                        Note.created_at < ninety_days_ago
                    )
                )
                notes_count = deleted_notes_res.rowcount

                # 2. Delete LongTermMemory with score < 5 older than 180 days
                deleted_ltm_res = await session.execute(
                    delete(LongTermMemory).where(
                        LongTermMemory.importance_score < 5,
                        LongTermMemory.created_at < one_eighty_days_ago
                    )
                )
                ltm_count = deleted_ltm_res.rowcount

                await session.commit()
                logger.info(f"Cleanup completed: deleted {notes_count} notes and {ltm_count} longterm memories")
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
                await session.rollback()
                raise e

    # Execute the async core in the current thread's event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If we are in a running loop (e.g. some workers), use create_task or run_coroutine_threadsafe
        # But for basic Celery worker threading, asyncio.run is usually safest or direct loop run
        loop.run_until_complete(run_cleanup())
    else:
        asyncio.run(run_cleanup())
