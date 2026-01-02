from loguru import logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from asgiref.sync import async_to_sync

from app.models import Note, User, NoteStatus
from infrastructure.database import AsyncSessionLocal
from infrastructure.config import settings
from infrastructure.storage import storage_client
from infrastructure.redis_client import short_term_memory

# Core Business Logic
from app.core.analyze_core import analyze_core
from app.core.audio import audio_processor

class NotePipeline:
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
                if note.status == NoteStatus.PENDING or not note.transcription_text:
                    await self._run_transcribe_stage(note, db)
                
                # --- STAGE 2: ANALYZE ---
                if note.status == NoteStatus.PROCESSING or (note.transcription_text and not note.ai_analysis):
                    await self._run_analyze_stage(note, db)

                # --- STAGE 3: SYNC ---
                if note.status == NoteStatus.ANALYZED or (note.ai_analysis and note.status != NoteStatus.COMPLETED):
                    await self._run_sync_stage(note, db)

                logger.info(f"[Pipeline] Completed processing for note: {note_id}")

            except Exception as e:
                logger.error(f"[Pipeline] Failed processing note {note_id}: {e}")
                import traceback
                traceback.print_exc()
                note.status = NoteStatus.FAILED
                
                # Try to clean up processing step message
                error_msg = str(e)[:100].replace('\n', ' ')
                note.processing_step = f"Error: {error_msg}"
                await db.commit()

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
                    await bot.send_message(chat_id=user.telegram_chat_id, text=msg, parse_mode="Markdown")
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
