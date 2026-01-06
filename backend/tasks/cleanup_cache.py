from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy import delete
from loguru import logger
import datetime

from infrastructure.database import AsyncSessionLocal
from app.models import CachedAnalysis

async def _cleanup_cache_async():
    """Deletes expired entries from semantic cache."""
    logger.info("Starting Semantic Cache cleanup...")
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Use direct delete query for efficiency
            stmt = delete(CachedAnalysis).where(CachedAnalysis.expires_at < now)
            result = await db.execute(stmt)
            await db.commit()
            
            # result.rowcount returns the number of deleted rows
            deleted_count = result.rowcount
            logger.info(f"Cache Cleanup: Removed {deleted_count} expired entries.")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache Cleanup failed: {e}")
            await db.rollback()
            return 0

@shared_task(name="cleanup_cache")
def cleanup_cache_task():
    return async_to_sync(_cleanup_cache_async)()
