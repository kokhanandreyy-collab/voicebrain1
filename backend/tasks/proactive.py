from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import desc, and_
from loguru import logger
import datetime
import json

from infrastructure.database import AsyncSessionLocal
from app.models import User, LongTermMemory, Note, NoteRelation
from app.services.ai_service import ai_service
from app.core.bot import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def _trigger_proactive_reminders_async():
    """Daily task to scan memories/graph and send proactive follow-ups."""
    logger.info("Starting proactive reminders scan...")
    async with AsyncSessionLocal() as db:
        # 1. Identify active users with Telegram
        threshold_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
        user_res = await db.execute(
            select(User).where(and_(User.telegram_chat_id != None, User.last_note_date >= threshold_date))
        )
        users = user_res.scalars().all()
        
        for user in users:
            try:
                # 2. Time window: roughly 7 days ago
                start_window = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)
                end_window = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6)
                
                # Fetch meaningful memories
                mem_res = await db.execute(
                    select(LongTermMemory)
                    .where(and_(
                        LongTermMemory.user_id == user.id,
                        LongTermMemory.created_at >= start_window,
                        LongTermMemory.created_at <= end_window,
                        LongTermMemory.importance_score >= 6.0
                    ))
                    .limit(5)
                )
                memories = mem_res.scalars().all()
                
                # Fetch graph relations for context
                graph_res = await db.execute(
                    select(NoteRelation)
                    .where(and_(
                        NoteRelation.created_at >= start_window,
                        NoteRelation.created_at <= end_window
                    ))
                    .order_by(desc(NoteRelation.strength))
                    .limit(5)
                )
                relations = graph_res.scalars().all()
                
                if not memories and not relations:
                    continue
                
                # Check User Global Setting
                prefs = user.adaptive_preferences or {}
                if not prefs.get("enable_proactive", True):
                    continue

                # 3. Compile context for DeepSeek
                context_parts = [f"Memory: {m.summary_text} (Score: {m.importance_score})" for m in memories]
                
                prompt = (
                    "You are a 'Proactive Memory' agent. Review these notes from the user's life exactly 7 days ago.\n"
                    "Goal: Identify if there is a highly relevant, unresolved, or meaningful topic to follow up on.\n"
                    "Output a JSON object: {\"question\": \"...\", \"relevance_score\": 0-10}.\n"
                    "Criteria: relevance_score should be high (8-10) only if it's a critical task or emotional event. "
                    "If mostly mundane, score low.\n"
                    "Language: Russian.\n"
                    f"Context:\n" + "\n".join(context_parts)
                )
                
                response_json = await ai_service.get_chat_completion([
                    {"role": "system", "content": "You are a proactive life-assistant. Output JSON only."},
                    {"role": "user", "content": prompt}
                ], response_format="json_object")
                
                try:
                    data = json.loads(response_json)
                    question = data.get("question")
                    score = data.get("relevance_score", 0)
                except:
                    logger.warning("Failed to parse proactive JSON")
                    continue
                
                # Requirement: Relevance > 7
                if score <= 7:
                    logger.info(f"Skipping proactive for user {user.id}: Low relevance {score}")
                    continue

                # Requirement: Limit 5/day. (Implicitly met as this job runs once daily and sends 1 msg)
                
                # 4. Notify via Telegram
                if bot and user.telegram_chat_id:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Да, давай", callback_data=f"proactive_yes:{user.id}"),
                            InlineKeyboardButton(text="❌ Нет, позже", callback_data="proactive_no")
                        ]
                    ])
                    
                    final_msg = f"💡 **Вспомнилось из прошлой недели:**\n\n{question}"
                    await bot.send_message(chat_id=user.telegram_chat_id, text=final_msg, parse_mode="Markdown", reply_markup=kb)
                    logger.info(f"Proactive reminder sent to {user.email}")
                    
            except Exception as e:
                logger.error(f"Error in proactive reminder for {user.id}: {e}")

@shared_task(name="proactive_reminders_daily")
def proactive_reminders():
    """Daily Celery entry point."""
    return async_to_sync(_trigger_proactive_reminders_async)()
