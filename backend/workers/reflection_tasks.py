from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import desc
from loguru import logger
import datetime

from infrastructure.database import AsyncSessionLocal
from app.models import User, Note, LongTermMemory
from app.services.ai_service import ai_service

async def _process_reflection_async(user_id: str):
    logger.info(f"Starting reflection for user {user_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch last 50 notes
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.transcription_text.isnot(None))
            .order_by(desc(Note.created_at))
            .limit(50)
        )
        notes = result.scalars().all()
        
        if not notes:
            logger.info("No notes found for reflection.")
            return

        # 2. Build Prompt
        notes_text = "\n\n".join([f"Date: {n.created_at}\nText: {n.transcription_text[:1000]}" for n in notes])
        
        prompt = (
            "Обобщи ключевые события, проекты, стиль общения, привычки, изменения пользователя. "
            "Сделай краткий summary (200–400 слов). Оцени важность 0–10. "
            "Также определи 'identity_summary' (стиль общения, приоритеты, ключевые слова). "
            "Верни JSON: { 'summary': '...', 'identity_summary': '...', 'importance_score': float }."
            f"\n\nПоследние заметки пользователя:\n{notes_text}"
        )
        
        # 3. Call DeepSeek
        try:
             import json
             response_text = await ai_service.get_chat_completion([
                 {"role": "system", "content": "You are a helpful assistant. Return ONLY valid JSON in Russian."},
                 {"role": "user", "content": prompt}
             ])
             
             cleaned = ai_service.clean_json_response(response_text)
             try:
                 data = json.loads(cleaned)
             except json.JSONDecodeError:
                 logger.error(f"Reflection JSON Decode Error: {response_text}")
                 return

             summary = data.get("summary", "")
             identity = data.get("identity_summary", "")
             score = float(data.get("importance_score", 5.0))
             
             if not summary:
                 logger.warning("Empty summary from reflection.")
                 return

             # 4. Save to LongTermMemory
             embedding = await ai_service.get_embedding(summary)
             
             memory = LongTermMemory(
                 user_id=user_id,
                 summary_text=summary,
                 embedding=embedding,
                 importance_score=score
             )
             db.add(memory)
             
             # 5. Update User Identity Logic
             if identity:
                 user_res = await db.execute(select(User).where(User.id == user_id))
                 user = user_res.scalars().first()
                 if user:
                     user.identity_summary = identity

             await db.commit()
             logger.info(f"Reflection saved for user {user_id} (Score: {score})")
             
        except Exception as e:
            logger.error(f"Reflection failed: {e}")

@shared_task(name="reflection.daily_task")
def reflection_daily(user_id: str):
    async_to_sync(_process_reflection_async)(user_id)

@shared_task(name="reflection.trigger_daily")
def trigger_daily_reflection():
    async_to_sync(_trigger_reflection_async)()

async def _trigger_reflection_async():
    logger.info("Triggering daily reflection for active users...")
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.last_note_date >= seven_days_ago))
        active_users = result.scalars().all()
        
        for user in active_users:
            logger.info(f"Queueing reflection for user {user.id}")
            reflection_daily.delay(user.id)
