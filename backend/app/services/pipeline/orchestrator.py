from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import OperationalError
import traceback

from app.models import Note, NoteStatus
from infrastructure.database import AsyncSessionLocal
from .stages import PipelineStages

class PipelineOrchestrator:
    """
    Manages the sequence and flow of pipeline stages.
    Handles error boundaries and state transitions between stages.
    """

    async def run(self, note_id: str):
        logger.info(f"[Pipeline] Starting process for note: {note_id}")
        
        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch State
                result = await db.execute(select(Note).where(Note.id == note_id))
                note = result.scalars().first()
                if not note:
                    logger.error(f"Note {note_id} not found")
                    return

                # 2. Stage 1: Transcription
                if note.status == NoteStatus.PENDING or not note.transcription_text:
                    try:
                        await PipelineStages.transcribe(note, db)
                    except Exception as e:
                        return await self._fail_stage(note, db, "Transcription", e)

                # 3. Stage 2: Analysis
                if note.status == NoteStatus.PROCESSING or (note.transcription_text and not note.ai_analysis):
                    try:
                        await PipelineStages.analyze(note, db)
                    except Exception as e:
                        return await self._fail_stage(note, db, "Analysis", e)

                # 4. Stage 3: Sync & Notify
                if note.status == NoteStatus.ANALYZED or (note.ai_analysis and note.status != NoteStatus.COMPLETED):
                    try:
                        await PipelineStages.sync(note, db)
                        await PipelineStages.notify(note, db)
                    except Exception as e:
                        # Sync failure is often non-fatal for local state
                        logger.error(f"[Pipeline] Sync stage warning: {e}")
                        note.status = NoteStatus.COMPLETED
                        note.processing_step = f"Sync Failed (Saved): {str(e)[:50]}"
                        await db.commit()

                logger.info(f"[Pipeline] Successfully processed note: {note_id}")

            except Exception as e:
                if isinstance(e, (OperationalError, OSError)):
                    logger.warning(f"[Pipeline] Transient error for {note_id}: {e}. Retrying via Celery...")
                    raise e
                
                logger.error(f"[Pipeline] Fatal error for note {note_id}: {e}")
                traceback.print_exc()
                note.status = NoteStatus.FAILED
                note.processing_step = f"Fatal Error: {str(e)[:100]}"
                await db.commit()

    async def _fail_stage(self, note: Note, db: AsyncSession, stage_name: str, error: Exception):
        logger.error(f"[Pipeline] {stage_name} stage failed: {error}")
        note.status = NoteStatus.FAILED
        note.processing_step = f"{stage_name} Failed: {str(error)[:50]}"
        await db.commit()
        return
