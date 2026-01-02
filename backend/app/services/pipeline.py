import asyncio
from typing import Optional, List
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from asgiref.sync import async_to_sync

from app.models import Note, User, Integration, NoteStatus
from app.core.database import AsyncSessionLocal
from app.services.ai_service import ai_service
from app.infrastructure.config import settings

# Core Logic
from app.core.analyze_core import analyze_core
from app.services.integrations import get_integration_handler
from app.utils.redis import short_term_memory

# Worker dependencies (imported dynamically or via interface to avoid circular imports? No, pipeline is called BY workers usually or pipeline calls logic)
# Actually, if pipeline is the orchestrator, it should contain the logic previously in _process_X_async.

# Transcribe Logic reused from tasks or moved here? 
# To avoid huge diff, we will import "step" functions from tasks if possible, OR re-implement clean logic here.
# User asked "Create services/pipeline.py - orchestrator". 
# "Call from workers".
# So logic should move to pipeline.py.

from workers.transcribe_tasks import step_download_audio, step_remove_silence, step_transcribe
from workers.sync_tasks import step_sync_integrations

class NotePipeline:
    def __init__(self):
        pass

    async def process(self, note_id: str):
        """
        Full orchestration: Transcribe -> Analyze -> Sync -> Notify
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
                # Update status to ERROR
                note.status = NoteStatus.FAILED
                note.processing_step = f"Error: {str(e)[:50]}"
                await db.commit()

    async def _run_transcribe_stage(self, note: Note, db: AsyncSession):
        logger.info(f"--- Stage 1: Transcribe ({note.id}) ---")
        note.status = NoteStatus.PROCESSING
        
        # 1. Download
        note.processing_step = "☁️ Uploading..."
        await db.commit()
        content = await step_download_audio(note)

        # 2. Optimize
        note.processing_step = "✂️ Optimizing audio..."
        await db.commit()
        content = await step_remove_silence(content)

        # 3. Transcribe
        note.processing_step = "🎙️ Transcribing audio..."
        await db.commit()
        text, duration = await step_transcribe(content)
        
        # 4. Update Note & Quota
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
        
        # 1. Fetch User Config
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()
        user_bio = user.bio if user else None
        target_lang = user.target_language if user else "Original"

        # 2. Build Context
        note.processing_step = "🧠 Recalling memories..."
        await db.commit()
        
        hierarchical_context = await analyze_core.build_hierarchical_context(note, db)

        # 3. Analyze
        note.processing_step = "🤖 AI Analysis..."
        await db.commit()
        
        analysis = await analyze_core.analyze_step(
            note.transcription_text, 
            user_context=user_bio, 
            target_language=target_lang,
            previous_context=hierarchical_context
        )

        # 4. Save
        await analyze_core.save_analysis(note, analysis, db)
        
        # 5. Short Term Memory Update
        await short_term_memory.add_action(note.user_id, {
            "type": "note_analyzed",
            "title": analysis.get("title"),
            "text": f"Analyzed note: {analysis.get('title')}. Summary: {analysis.get('summary')[:100]}..."
        })
        
        note.status = NoteStatus.ANALYZED
        await db.commit()

    async def _run_sync_stage(self, note: Note, db: AsyncSession):
        logger.info(f"--- Stage 3: Sync ({note.id}) ---")
        note.processing_step = "🚀 Syncing with apps..."
        await db.commit()

        # 1. Sync Logic (from workers.sync_tasks mostly)
        await step_sync_integrations(note, db)
        
        # 2. Finalize
        note.status = NoteStatus.COMPLETED
        note.processing_step = "Completed"
        await db.commit()
        
        # 3. Notify
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
                logger.warning("pywebpush not installed")

pipeline = NotePipeline()
