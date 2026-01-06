from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy.future import select
from loguru import logger
import datetime
import json

from infrastructure.database import AsyncSessionLocal
from app.models import User, LongTermMemory, Note
from app.services.ai_service import ai_service
from app.core.bot import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def _trigger_proactive_reminders_async():
    """Daily task to scan memories and send proactive follow-ups."""
    logger.info("Starting proactive reminders scan...")
    async with AsyncSessionLocal() as db:
        # 1. Identify active users (last note within 14 days)
        threshold_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
        user_res = await db.execute(select(User).where(User.telegram_chat_id != None, User.last_note_date >= threshold_date))
        users = user_res.scalars().all()
        
        for user in users:
            try:
                # 2. Find meaningful memories from ~7 days ago (window 6-8 days)
                start_window = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)
                end_window = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6)
                
                mem_res = await db.execute(
                    select(LongTermMemory)
                    .where(
                        LongTermMemory.user_id == user.id,
                        LongTermMemory.created_at >= start_window,
                        LongTermMemory.created_at <= end_window,
                        LongTermMemory.importance_score >= 7.0
                    )
                    .limit(3)
                )
                memories = mem_res.scalars().all()
                
                if not memories:
                    continue
                
                # 3. Generate proactive question using AI
                memory_context = "\n".join([f"- {m.summary_text}" for m in memories])
                
                prompt = (
                    "Based on these memories from last week, generate one thoughtful follow-up question. "
                    "Goal: show care, ask about progress, or offer help. "
                    "Keep it short (under 25 words). Language: Russian. "
                    f"\n\nMemories:\n{memory_context}"
                )
                
                question = await ai_service.get_chat_completion([
                    {"role": "system", "content": "You are a supportive AI companion. Ask a follow-up about past thoughts."},
                    {"role": "user", "content": prompt}
                ])
                
                # 4. Send to Telegram
                if bot:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="👍 Да, давай", callback_data=f"proactive_yes:{user.id}"),
                            InlineKeyboardButton(text="👎 Нет, позже", callback_data="proactive_no")
                        ]
                    ])
                    
                    msg = f"🤔 **Вспомнилось из прошлой недели:**\n\n{question}"
                    await bot.send_message(chat_id=user.telegram_chat_id, text=msg, parse_mode="Markdown", reply_markup=kb)
                    logger.info(f"Proactive reminder sent to user {user.id}")
                    
            except Exception as e:
                logger.error(f"Failed proactive reminder for user {user.id}: {e}")

@shared_task(name="proactive_reminders_daily")
def proactive_reminders():
    return async_to_sync(_trigger_proactive_reminders_async)()
