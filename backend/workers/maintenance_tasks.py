import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.models import Note, User, NoteEmbedding, UserTier
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.storage import storage_client
from app.services.ai_service import ai_service
from app.infrastructure.http_client import http_client
from app.infrastructure.config import settings

@celery.task(name="cluster_notes")
def cluster_notes_task(user_id: str):
    async_to_sync(_cluster_notes_async)(user_id)
    return {"status": "success", "user_id": user_id}

async def _cluster_notes_async(user_id: str) -> None:
    logger.info(f"Clustering for user: {user_id}")
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(Note).join(NoteEmbedding).where(Note.user_id == user_id, Note.status == 'COMPLETED'))
        notes = list(result.scalars().all())
        if len(notes) < 3: return

        import numpy as np
        from sklearn.cluster import KMeans
        embeddings = [n.embedding_data.embedding for n in notes if n.embedding_data]
        if not embeddings: return

        X = np.array(embeddings)
        n_clusters = max(2, min(5, len(notes) // 2))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        for i, note in enumerate(notes):
            note.cluster_id = f"topic_{labels[i]}"
        await db.commit()
    except Exception as e: logger.error(f"Clustering error: {e}")
    finally: await db.close()

@celery.task(name="cleanup_old_notes")
def cleanup_old_notes_task():
    async_to_sync(_cleanup_old_notes_async)()

async def _cleanup_old_notes_async() -> None:
    from datetime import datetime, timedelta, timezone
    
    logger.info("Starting retention cleanup...")
    db: AsyncSession = AsyncSessionLocal()
    try:
        now: datetime = datetime.now(timezone.utc)
        cutoff_free: datetime = now - timedelta(days=90)
        cutoff_pro: datetime = now - timedelta(days=365)
        
        async def delete_batch(notes: List[Note]) -> int:
            count: int = 0
            for note in notes:
                key: Optional[str] = note.storage_key
                if key:
                    try: await storage_client.delete_file(key)
                    except Exception as s3_err: logger.warning(f"Failed to delete file {key}: {s3_err}")
                await db.delete(note)
                count += 1
            return count

        res_free = await db.execute(select(Note).join(User).where(User.tier == UserTier.FREE, Note.created_at < cutoff_free))
        c_free: int = await delete_batch(list(res_free.scalars().all()))
        
        res_pro = await db.execute(select(Note).join(User).where(User.tier == UserTier.PRO, Note.created_at < cutoff_pro))
        c_pro: int = await delete_batch(list(res_pro.scalars().all()))

        await db.commit()
        logger.info(f"Cleanup complete. Deleted {c_free} Free and {c_pro} Pro notes.")
    except Exception as e: logger.error(f"Cleanup Error: {e}")
    finally: await db.close()

@celery.task(name="check_subscription_expiry")
def check_subscription_expiry_task():
    async_to_sync(_check_subscription_expiry_async)()

async def _check_subscription_expiry_async() -> None:
    from app.services.email import send_email
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(User).where(User.tier.in_([UserTier.PRO, UserTier.PREMIUM])))
        users = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        notified_count = 0
        for user in users:
            if not user.billing_cycle_start: continue
            cycle_start = user.billing_cycle_start.replace(tzinfo=timezone.utc) if user.billing_cycle_start.tzinfo is None else user.billing_cycle_start
            period = timedelta(days=365) if user.billing_period == 'yearly' else timedelta(days=30)
            renewal_date = cycle_start
            while renewal_date < now: renewal_date += period
            time_until = renewal_date - now
            if time_until.days == 3:
                saved_hours = int(((user.monthly_usage_seconds or 0) * 3) / 3600)
                subject = f"VoiceBrain Subscription Update"
                body = f"Hi {user.full_name}, your subscription will renew on {renewal_date.strftime('%B %d, %Y')}."
                await send_email(user.email, subject, body)
                notified_count += 1
        logger.info(f"Expiry check complete. Sent {notified_count} notifications.")
    except Exception as e: logger.error(f"Expiry Check Error: {e}")
    finally: await db.close()

@celery.task(name="backup_database")
def backup_database_task():
    async_to_sync(_backup_database_async)()

async def _backup_database_async() -> None:
    import subprocess, gzip
    logger.info("Starting database backup...")
    pg_user, pg_password, pg_host = settings.POSTGRES_USER, settings.POSTGRES_PASSWORD, settings.POSTGRES_HOST
    pg_port, pg_db = settings.POSTGRES_PORT, settings.POSTGRES_DB
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"/tmp/voicebrain_db_{timestamp}.sql.gz"
    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password
    try:
        with gzip.open(backup_path, 'wb') as f_out:
            cmd = ['pg_dump', '-h', pg_host, '-p', pg_port, '-U', pg_user, pg_db]
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0: return
            f_out.write(proc.stdout)
        with open(backup_path, "rb") as f_in:
             await storage_client.upload_file(f_in, f"backups/{os.path.basename(backup_path)}", content_type="application/gzip")
        logger.info("Backup uploaded successfully")
    except Exception as e: logger.error(f"Backup failure: {e}")
    finally:
        if os.path.exists(backup_path): os.remove(backup_path)

@celery.task(name="generate_weekly_review")
def generate_weekly_review_task():
    async_to_sync(_generate_weekly_review_async)()

async def _generate_weekly_review_async() -> None:
    db = AsyncSessionLocal()
    http_client.start()
    try:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        res = await db.execute(select(Note.user_id).where(Note.created_at >= seven_days_ago).distinct())
        for user_id in res.scalars().all():
            if not user_id: continue 
            notes_res = await db.execute(select(Note).where(Note.user_id == user_id, Note.created_at >= seven_days_ago, Note.status == 'COMPLETED'))
            notes = list(notes_res.scalars().all())
            if len(notes) < 3: continue
            u_res = await db.execute(select(User).where(User.id == user_id))
            user = u_res.scalars().first()
            if not user: continue
            review_text = await ai_service.analyze_weekly_notes("\n".join([f"- {n.title}: {n.summary}" for n in notes if n.summary]))
            db.add(Note(user_id=user_id, title=f"Weekly Review: {seven_days_ago.date()}", transcription_text="System review", summary=review_text, status="COMPLETED", is_audio_note=False))
        await db.commit()
    except Exception as e: logger.error(f"Weekly Review Error: {e}")
    finally: await db.close()
