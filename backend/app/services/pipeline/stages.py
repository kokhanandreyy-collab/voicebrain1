from loguru import logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from app.models import Note, User, NoteStatus
from infrastructure.storage import storage_client
from app.core.audio import audio_processor
from app.core.analyze_core import analyze_core
from infrastructure.redis_client import short_term_memory
from infrastructure.config import settings

class PipelineStages:
    """
    Individual execution stages of the Note processing pipeline.
    Each stage is idempotent and includes retry logic for transient errors.
    """

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def transcribe(note: Note, db: AsyncSession):
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

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def analyze(note: Note, db: AsyncSession):
        logger.info(f"--- Stage 2: Analyze ({note.id}) ---")
        note.processing_step = "AI Analysis..."
        await db.commit()

        # Fetch User
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()

        # Use Core Analyze (includes RAG + Intent)
        analysis, cache_hit = await analyze_core.analyze_step(note, user, db, short_term_memory)
        
        # Store cache status in analysis blob for later logging if needed
        if isinstance(note.ai_analysis, dict):
             note.ai_analysis["_cache_hit"] = cache_hit
        
        note.status = NoteStatus.ANALYZED
        await db.commit()

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, ConnectionError, TimeoutError, OSError)))
    async def sync(note: Note, db: AsyncSession):
        logger.info(f"--- Stage 3: Sync ({note.id}) ---")
        
        # Check Feature Flags
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()
        flags = user.feature_flags or {} if user else {}
        
        if not flags.get("all_integrations", True) and not flags.get("sync_enabled", True):
            logger.info(f"Sync skipped for user {note.user_id} due to feature flags")
            note.status = NoteStatus.COMPLETED
            note.processing_step = "Sync Skipped (Disabled)"
            await db.commit()
            return

        note.processing_step = "Syncing..."
        await db.commit()

        # Use Core Sync Service
        from app.core.sync_service import sync_service
        await sync_service.sync_note(note, db)
        
        note.status = NoteStatus.COMPLETED
        note.processing_step = "Completed"
        await db.commit()

    @staticmethod
    async def notify(note: Note, db: AsyncSession):
        """Notifies user via Telegram and Push on completion."""
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
                    empathy = (note.ai_analysis or {}).get("empathetic_comment")
                    
                    msg = f"✅ **Saved!**\n"
                    if empathy:
                        msg += f"_{escape_markdown(empathy)}_\n\n"
                    
                    msg += f"Title: {safe_title}\nIntent: {safe_intent}"

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
