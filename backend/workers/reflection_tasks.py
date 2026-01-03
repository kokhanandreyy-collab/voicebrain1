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
            "Сделай краткий summary (200–400 слов). Оцени важность 0–10 (где 10 = критически важное, меняющее жизнь событие). "
            "Также определи 'identity_summary': Стиль общения, приоритеты, жаргон, привычки пользователя. Кратко, 100–200 слов. "
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
                 user_obj = user_res.scalars().first()
                 if user_obj:
                     user_obj.identity_summary = identity
             
             # 6. Graph Relations (New)
             try:
                 # Specific strict prompt as requested
                 rel_prompt = (
                     "Генерируй связи строго в JSON list: "
                     "[{'note1_id': str, 'note2_id': str, 'type': 'caused|related|updated|contradicted', 'strength': float 0.5–1.0}]. "
                     "Используй ID заметок (UUID), предоставленные ниже."
                     f"\n\nЗаметки:\n"
                 )
                 notes_data = [{"id": n.id, "text": n.transcription_text[:200]} for n in notes]
                 rel_prompt += json.dumps(notes_data, ensure_ascii=False)
                 
                 rel_resp = await ai_service.get_chat_completion([
                     {"role": "system", "content": "You are a graph database agent. Return ONLY JSON list."},
                     {"role": "user", "content": rel_prompt}
                 ])
                 
                 cleaned_resp = ai_service.clean_json_response(rel_resp)
                 if not cleaned_resp:
                     logger.warning("Empty AI response during graph extraction.")
                     return

                 try:
                     raw_data = json.loads(cleaned_resp)
                 except json.JSONDecodeError:
                     logger.error(f"Failed to decode Graph JSON: {rel_resp[:200]}...")
                     return

                 relations = raw_data if isinstance(raw_data, list) else raw_data.get("relations", [])
                 logger.info(f"Graph extraction: generated {len(relations)} connections")
                 
                 from app.models import NoteRelation
                 added_count = 0
                 for r in relations:
                     n1 = r.get('note1_id') or r.get('id1')
                     n2 = r.get('note2_id') or r.get('id2')
                     r_type = r.get('type') or r.get('relation_type', 'related')
                     try:
                         r_strength = float(r.get('strength', 1.0))
                     except (TypeError, ValueError):
                         r_strength = 1.0
                     
                     if n1 and n2:
                         nr = NoteRelation(
                             note_id1=n1,
                             note_id2=n2,
                             relation_type=r_type,
                             strength=r_strength
                         )
                         db.add(nr)
                         added_count += 1
                 
                 if added_count > 0:
                     logger.debug(f"Saved {added_count} new note relations to DB.")
                         
             except Exception as rel_err:
                 logger.error(f"Graph extraction failed: {rel_err}")

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
