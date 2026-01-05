from loguru import logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError
from asgiref.sync import async_to_sync

from app.models import Note, User, NoteStatus
from infrastructure.database import AsyncSessionLocal
from infrastructure.config import settings
from infrastructure.storage import storage_client
from infrastructure.redis_client import short_term_memory

# Core Business Logic
from app.core.analyze_core import analyze_core
from app.core.audio import audio_processor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

class NotePipeline:
    """
    Orchestrates the lifecycle of a Voice Note processing job.

    Stages:
    1. Transcribe: Audio -> Text (via AssemblyAI/DeepSeek/local whisper).
    2. Analyze: Text -> Structured Insights (Intent, Action Items, Summary) + RAG Context.
    3. Sync: Insights -> External Tools (Notion, Slack, etc.) + Notifications.

    Features:
    - Fault Tolerance: Each stage is isolated; failures don't crash the worker.
    - Resilience: Uses `tenacity` for retrying transient network/API errors.
    - Monitoring: detailed logging and status updates to the Note model.
    """
    async def process(self, note_id: str):
        """
        Orchestration: Transcribe -> Analyze (Intent+RAG) -> Sync
        """
        logger.info(f"[Pipeline] Starting process for note: {note_id}")
        
        async with AsyncSessionLocal() as db:
            try:
                # 0. Fetch Note
                result = await db.execute(select(Note).where(Note.id == note_id))
                note = result.scalars().first()
                if not note:
                    logger.error(f"Note {note_id} not found in pipeline")
                    return

                # --- STAGE 1: TRANSCRIBE ---
                try:
                    if note.status == NoteStatus.PENDING or not note.transcription_text:
                        await self._run_transcribe_stage(note, db)
                except Exception as e:
                    logger.error(f"[Pipeline] Transcription stage failed: {e}")
                    note.status = NoteStatus.FAILED
                    note.processing_step = f"Transcription Failed: {str(e)[:50]}"
                    await db.commit()
                    return # Stop pipeline if transcription fails

                # --- STAGE 2: ANALYZE ---
                try:
                    if note.status == NoteStatus.PROCESSING or (note.transcription_text and not note.ai_analysis):
                        await self._run_analyze_stage(note, db)
                except Exception as e:
                    logger.error(f"[Pipeline] Analysis stage failed: {e}")
                    note.status = NoteStatus.FAILED
                    note.processing_step = f"Analysis Failed: {str(e)[:50]}"
                    await db.commit()
                    return # Stop pipeline if analysis fails

                # --- STAGE 3: SYNC ---
                try:
                    if note.status == NoteStatus.ANALYZED or (note.ai_analysis and note.status != NoteStatus.COMPLETED):
                        await self._run_sync_stage(note, db)
                except Exception as e:
                    logger.error(f"[Pipeline] Sync stage failed: {e}")
                    # Non-fatal? Maybe. But let's mark as completed with warning or just log.
                    # We'll mark as COMPLETED but logging the error in step
                    note.status = NoteStatus.COMPLETED
                    note.processing_step = f"Sync Failed (Saved Locally): {str(e)[:50]}"
                    await db.commit()

                logger.info(f"[Pipeline] Completed processing for note: {note_id}")

            except Exception as e:
                # Re-raise transient errors for Celery retry
                if isinstance(e, (OperationalError, OSError)):
                    logger.warning(f"[Pipeline] Transient error for {note_id}: {e}. Retrying...")
                    raise e
                
                logger.error(f"[Pipeline] Failed processing note {note_id}: {e}")
                import traceback
                traceback.print_exc()
                note.status = NoteStatus.FAILED
                
                # Try to clean up processing step message
                error_msg = str(e)[:100].replace('\n', ' ')
                note.processing_step = f"Error: {error_msg}"
                await db.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def _run_transcribe_stage(self, note: Note, db: AsyncSession):
        logger.info(f"--- Stage 1: Transcribe ({note.id}) ---")
        note.status = NoteStatus.PROCESSING
        note.processing_step = "Processing Audio..."
        await db.commit()

        # Use Core Audio Processor
        text, duration = await audio_processor.process_audio(note, storage_client)
        
        note.transcription_text = text
        if duration > 0:
            est = note.duration_seconds or 0
            note.duration_seconds = duration
            # Update user monthly usage
            user_res = await db.execute(select(User).where(User.id == note.user_id))
            user = user_res.scalars().first()
            if user:
                diff = duration - est
                user.monthly_usage_seconds = max(0, user.monthly_usage_seconds + diff)
        
        await db.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def _run_analyze_stage(self, note: Note, db: AsyncSession):
        logger.info(f"--- Stage 2: Analyze ({note.id}) ---")
        note.processing_step = "AI Analysis..."
        await db.commit()

        # Fetch User
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()

        # Use Core Analyze (includes RAG + Intent)
        await analyze_core.analyze_step(note, user, db, short_term_memory)
        
        note.status = NoteStatus.ANALYZED
        await db.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def _run_sync_stage(self, note: Note, db: AsyncSession):
        logger.info(f"--- Stage 3: Sync ({note.id}) ---")
        
        # Check Feature Flags
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()
        flags = user.feature_flags or {} if user else {}
        
        if not flags.get("all_integrations", True) and not flags.get("sync_enabled", True): # Fallback or specific override
            logger.info(f"Sync skipped for user {note.user_id} due to feature flags")
            # We still complete the note to not hang it forever
            note.status = NoteStatus.COMPLETED
            note.processing_step = "Sync Skipped (Disabled)"
            await db.commit()
            return

        note.processing_step = "Syncing..."
        await db.commit()

        # Use Core Sync Service (To be created)
        from app.core.sync_service import sync_service
        await sync_service.sync_note(note, db)
        
        note.status = NoteStatus.COMPLETED
        note.processing_step = "Completed"
        await db.commit()
        
        # Notify
        await self._notify_completion(note, db)

    async def _notify_completion(self, note: Note, db: AsyncSession):
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()
        if not user: return

        # Telegram
        if user.telegram_chat_id:
            from app.core.bot import bot
            from common.utils import escape_markdown
            if bot:
                try:
                    safe_title = escape_markdown(note.title or "Untitled")
                    safe_intent = escape_markdown((note.ai_analysis or {}).get("intent", "note"))
                    msg = f"✅ **Saved!**\nTitle: {safe_title}\nIntent: {safe_intent}"

                    # Check for adaptive clarification
                    if note.action_items:
                        for item in note.action_items:
                            if "Clarification Needed:" in str(item):
                                question = str(item).replace("Clarification Needed:", "").strip()
                                msg += f"\n\n❓ **Question:** {escape_markdown(question)}\n_Reply to answer_"
                                break
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="👁️ View Details", callback_data=f"view_note:{note.id}")]
                    ])
                    await bot.send_message(chat_id=user.telegram_chat_id, text=msg, parse_mode="Markdown", reply_markup=kb)
                except Exception as e: logger.warning(f"TG notify failed: {e}")

        # Push
        if user.push_subscriptions and settings.VAPID_PRIVATE_KEY:
            try:
                from pywebpush import webpush
                import json
                payload = json.dumps({"title": "Note Processed", "body": f"{note.title} analyzed.", "url": f"/dashboard?note={note.id}"})
                for sub in user.push_subscriptions:
                    try:
                        webpush(subscription_info=sub, data=payload, vapid_private_key=settings.VAPID_PRIVATE_KEY, vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL})
                    except Exception: pass
            except ImportError:
               pass

pipeline = NotePipeline()
