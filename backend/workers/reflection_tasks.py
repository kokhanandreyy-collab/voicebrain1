from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy import func

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User, LongTermSummary
from app.core.database import AsyncSessionLocal

async def _reflection_summary_async(user_id: str):
    """
    Analyzes last 50 notes to generate a long-term summary of themes and habits.
    """
    logger.info(f"[Reflection] Starting for user: {user_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch last 50 notes
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.status == "COMPLETED")
            .order_by(Note.created_at.desc())
            .limit(50)
        )
        notes = result.scalars().all()
        
        if not notes:
            logger.info(f"[Reflection] No completed notes for user {user_id}")
            return

        # 2. Prepare Context
        notes_context = "\n---\n".join([
            f"Title: {n.title}\nSummary: {n.summary}" 
            for n in notes if n.summary
        ])
        
        if not notes_context:
            logger.info(f"[Reflection] No summaries available for user {user_id}")
            return

        # 3. Generate Reflection via DeepSeek
        prompt = (
            "You are VoiceBrain Reflection Engine. Analyze the following user notes from the recent period. "
            "Identify: 1. Key recurring themes and projects. 2. Communication style and dominant moods. "
            "3. Personal habits, preferences, or jargon mentioned. 4. Progress on long-term goals. "
            "Write a concise, high-level summary (approx 300 words) that captures the 'essence' of the user's recent thoughts. "
            "Format with Markdown."
        )
        
        # We reuse analyze_text logic but with a custom system prompt override
        # Or better, a direct call to DeepSeek via ai_service if we had a dedicated Method.
        # For now, let's use a simplified approach.
        
        reflection_text = await ai_service.ask_notes(notes_context, prompt)
        
        # 4. Generate Embedding
        vector = await ai_service.generate_embedding(reflection_text)
        
        # 5. Save to LongTermSummary
        new_summary = LongTermSummary(
            user_id=user_id,
            summary_text=reflection_text,
            embedding=vector,
            importance_score=8.0 # High priority for reflection
        )
        db.add(new_summary)
        await db.commit()
        logger.info(f"[Reflection] Completed and saved for user {user_id}")

async def _trigger_reflections_async():
    """
    Identifies active users (active in last 7 days) and triggers reflection tasks.
    """
    logger.info("[Reflection] Scanning for active users...")
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    async with AsyncSessionLocal() as db:
        # Users who created a note in the last 7 days
        # We use a subquery to find unique user_ids from recent notes
        recent_users_query = select(Note.user_id).where(Note.created_at >= seven_days_ago).distinct()
        result = await db.execute(recent_users_query)
        user_ids = result.scalars().all()
        
        logger.info(f"[Reflection] Found {len(user_ids)} active users for reflection")
        for uid in user_ids:
            reflection_summary.delay(uid)

@celery.task(name="reflection.summary")
def reflection_summary(user_id: str):
    async_to_sync(_reflection_summary_async)(user_id)

@celery.task(name="reflection.trigger_daily")
def trigger_daily_reflections():
    async_to_sync(_trigger_reflections_async)()
