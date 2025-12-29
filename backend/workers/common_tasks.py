from typing import Optional
from loguru import logger
from sqlalchemy.future import select
from app.models import Note, User
from app.core.database import AsyncSessionLocal

async def handle_note_failure(note_id: str, error_msg: str) -> None:
    """Centralized failure handler for note processing stages."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Note).where(Note.id == note_id))
            note = result.scalars().first()
            
            if note:
                note.status = "FAILED"
                note.processing_error = error_msg
                
                # Refund User Quota
                estimated = note.duration_seconds or 0
                if estimated > 0:
                    res_u = await db.execute(select(User).where(User.id == note.user_id))
                    user = res_u.scalars().first()
                    if user:
                        user.monthly_usage_seconds = max(0, user.monthly_usage_seconds - estimated)
                        logger.info(f"Refunded {estimated}s to user {user.id} due to failure.")
                
                await db.commit()
                logger.info(f"Marked note {note_id} as FAILED: {error_msg}")
    except Exception as db_e:
        logger.critical(f"Critical DB Error during failure handling for {note_id}: {db_e}")
