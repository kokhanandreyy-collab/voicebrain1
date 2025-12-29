from typing import List, Optional, Tuple, Any, Dict, Union
import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import inspect
from urllib.parse import urlparse

# Third-party
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# Local
from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, Integration, User, IntegrationLog, NoteEmbedding, UserTier
from app.core.database import AsyncSessionLocal
from app.core.storage import storage_client
from app.services.integrations import get_integration_handler
from app.core.http_client import http_client 
from app.core.types import AIAnalysisPack

# Configure Logging (already defined logger from loguru)
# logger = logging.getLogger(__name__) # Removed in favor of loguru

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown V1."""
    if not text:
        return ""
    # Characters to escape in Markdown V1: _ * [ `
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f'\\{char}')
    return text

async def step_download_audio(note: Note, db: AsyncSession) -> bytes:
    """Download audio content from storage."""
    # 1. Primary: Storage Key
    if note.storage_key:
        try:
            return await storage_client.read_file(note.storage_key)
        except Exception as e:
            logger.error(f"Failed to read file from storage key {note.storage_key}: {e}")
            raise

    # 2. Fallback: Parse from URL (if legacy data exists)
    if note.audio_url:
        try:
            path = urlparse(note.audio_url).path
            key = os.path.basename(path) # clearer than split
            if key:
                logger.info(f"Attempting fallback download with key: {key}")
                return await storage_client.read_file(key)
        except (ValueError, KeyError) as e:
            logger.warning(f"Fallback key extraction failed (likely URL format): {e}")
        except Exception as e:
            logger.warning(f"Fallback download failed unexpectedly: {e}")

    raise ValueError(f"Could not determine storage key for note {note.id}")

async def step_remove_silence(content: bytes) -> bytes:
    """Use FFmpeg to remove silence > 1s from audio."""
    if not shutil.which('ffmpeg'):
        logger.warning("ffmpeg not found, skipping silence removal")
        return content

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as input_tmp:
        input_tmp.write(content)
        input_path = input_tmp.name

    output_path = input_path.replace(".webm", "_optimized.webm")

    try:
        # ffmpeg command to remove silence
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-af', 'silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-30dB',
            '-c:a', 'libopus', # Re-encode to opus/webm
            output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate() 

        if proc.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                with open(output_path, "rb") as f_out:
                    optimized_content = f_out.read()
                
                original_size = len(content)
                savings = (1 - (file_size / original_size)) * 100
                logger.info(f"Silence removal successful. Size reduced by {savings:.1f}% ({original_size/1024:.1f}KB -> {file_size/1024:.1f}KB)")
                return optimized_content
            else:
                 logger.warning("FFmpeg produced empty file")
        else:
            logger.warning(f"FFmpeg failed (rc={proc.returncode}): {stderr.decode()}")
            
        return content
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Silence removal OS/Subprocess error: {e}")
        return content
    except Exception as e:
        logger.error(f"Silence removal unexpected error: {e}")
        return content
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except Exception as rm_e: logger.debug(f"Failed to remove tmp file {p}: {rm_e}")

async def step_transcribe(content: bytes) -> Tuple[str, int]:
    """Transcribe audio and calculate precise duration."""
    real_duration_sec: int = 0
    
    # Temporary save for ffprobe
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        if shutil.which('ffprobe'):
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', tmp_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
                if proc.returncode == 0:
                    output_val = stdout.decode().strip()
                    if output_val and output_val != 'N/A':
                        real_duration_sec = int(float(output_val))
                        logger.info(f"FFPROBE duration: {real_duration_sec}s")
                else:
                    logger.warning(f"FFprobe failed (rc={proc.returncode}): {stderr.decode()}")

            except asyncio.TimeoutError:
                logger.warning("FFProbe timed out, killing...")
                try:
                    proc.kill()
                    await proc.wait()
                except Exception as kill_err: 
                    logger.debug(f"Failed to kill ffprobe: {kill_err}")
    except (subprocess.SubprocessError, OSError) as probe_err:
        logger.warning(f"Duration analysis (ffprobe) failed: {probe_err}")
    except Exception as probe_err:
        logger.warning(f"Duration analysis unexpected error: {probe_err}")
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception as rm_e: logger.debug(f"Failed to remove tmp file {tmp_path}: {rm_e}")

    transcription = await ai_service.transcribe_audio(content)
    text: str = transcription["text"]
    return text, real_duration_sec

async def step_analyze(text: str, user_context: Optional[str] = None, target_language: str = "Original") -> Dict[str, Any]:
    """Analyze text using AI service."""
    return await ai_service.analyze_text(text, user_context=user_context, target_language=target_language)

async def step_embed_and_save(note: Note, text: str, analysis: Dict[str, Any], db: AsyncSession) -> None:
    """Update note metadata and generate embeddings."""
    note.transcription_text = text
    note.title = analysis.get("title", "Untitled Note")
    note.summary = analysis.get("summary")
    note.action_items = analysis.get("action_items", [])
    note.calendar_events = analysis.get("calendar_events", [])
    note.tags = analysis.get("tags", [])
    note.diarization = analysis.get("diarization", [])
    note.mood = analysis.get("mood", "Neutral")
    note.health_data = analysis.get("health_data")
    
    # Pack Agentic Workflow Metadata
    note.ai_analysis = AIAnalysisPack(
        intent=analysis.get("intent", "note"),
        suggested_project=analysis.get("suggested_project", "Inbox"),
        entities=analysis.get("entities", []),
        priority=analysis.get("priority", 4),
        notion_properties=analysis.get("notion_properties", {}),
        explicit_destination_app=analysis.get("explicit_destination_app"),
        explicit_folder=analysis.get("explicit_folder")
    )
    
    # Embedding
    search_content: str = f"{note.title} {note.summary} {text} {' '.join(note.tags)}"
    try:
        embedding_vector: List[float] = await ai_service.generate_embedding(search_content)
        note_embedding = NoteEmbedding(note_id=note.id, embedding=embedding_vector)
        db.add(note_embedding)
    except Exception as e:
        logger.error(f"Failed to generate/save embedding for note {note.id}: {e}")

async def step_sync_integrations(note: Note, db: AsyncSession) -> None:
    """Sync processed note with enabled integrations."""
    # 1. Check for Explicit Routing
    ai_analysis_data: Dict[str, Any] = note.ai_analysis or {}
    explicit_app: Optional[str] = ai_analysis_data.get("explicit_destination_app")
    
    int_result = await db.execute(select(Integration).where(
        Integration.user_id == note.user_id
    ).options(selectinload(Integration.user)))
    user_integrations: List[Integration] = list(int_result.scalars().all())

    # If explicit app specified, filter to only that one
    if explicit_app:
        user_integrations = [i for i in user_integrations if i.provider == explicit_app]
        logger.info(f"Explicit Routing detected. Syncing ONLY to: {explicit_app}")

    for integration in user_integrations:
        handler = get_integration_handler(integration.provider)
        if handler:
            status_log: str = "SUCCESS"
            error_msg: Optional[str] = None
            try:
                # Inspect if handler.sync accepts 'db'
                sig = inspect.signature(handler.sync)
                if 'db' in sig.parameters:
                      await handler.sync(integration, note, db=db)
                else:
                      await handler.sync(integration, note)
            except Exception as int_err:
                logger.error(f"Integration sync failed for provider {integration.provider}: {int_err}")
                status_log = "FAILED"
                error_msg = str(int_err)
            
            log_entry = IntegrationLog(
                integration_id=integration.id,
                note_id=note.id,
                status=status_log,
                error_message=error_msg
            )
            db.add(log_entry)
        else:
            logger.debug(f"No handler for {integration.provider}")

async def _process_note_async(note_id: str) -> None:
    logger.info(f"Starting processing for note: {note_id}")
    
    # Ensure client is started (idempotent)
    http_client.start()
    
    db: AsyncSession = AsyncSessionLocal()
    try:
            # 1. Fetch Note
            result = await db.execute(select(Note).where(Note.id == note_id))
            note: Optional[Note] = result.scalars().first()
            if not note:
                logger.error(f"Note {note_id} not found")
                return
            
            # Capture estimated duration (already deducted by API)
            estimated_duration: int = note.duration_seconds or 0
            
            # --- Pipeline execution ---
            note.processing_step = "☁️ Uploading..."
            await db.commit()
            
            content: bytes = await step_download_audio(note, db)
            
            # Optimization
            note.processing_step = "✂️ Optimizing audio..."
            await db.commit()
            content = await step_remove_silence(content)

            note.processing_step = "🎙️ Transcribing audio..."
            await db.commit()
            
            text, real_duration_sec = await step_transcribe(content)
            
            # Quota Adjustment: Reconcile Estimate vs Actual
            if real_duration_sec > 0:
                note.duration_seconds = real_duration_sec
                
                user_result = await db.execute(select(User).where(User.id == note.user_id))
                user_record: Optional[User] = user_result.scalars().first()
                if user_record:
                    diff: int = real_duration_sec - estimated_duration
                    user_record.monthly_usage_seconds = max(0, user_record.monthly_usage_seconds + diff)
                    logger.info(f"Quota adjusted: {diff:+d}s")

            # Intermediate commit for progressive rendering
            note.transcription_text = text
            note.processing_step = "🧠 Extracting action items..."
            await db.commit()
            
            # Fetch User Bio & Lang
            user_bio: Optional[str] = None
            target_lang: str = "Original"
            if note.user_id:
                u_res = await db.execute(select(User).where(User.id == note.user_id))
                u: Optional[User] = u_res.scalars().first()
                if u:
                    if u.bio: user_bio = u.bio
                    if u.target_language: target_lang = u.target_language

            analysis: Dict[str, Any] = await step_analyze(text, user_context=user_bio, target_language=target_lang)
            
            await step_embed_and_save(note, text, analysis, db)
            
            note.processing_step = "🚀 Syncing with apps..."
            await db.commit()
            
            await step_sync_integrations(note, db)
            
            note.status = "COMPLETED"
            note.processing_step = "Completed"
            
            # Final Commit
            await db.commit()
            logger.info(f"Successfully processed note {note_id}")
            
            # 5. Telegram Feedback Loop
            if note.status == "COMPLETED" and note.user_id:
                user_res = await db.execute(select(User).where(User.id == note.user_id))
                user_obj: Optional[User] = user_res.scalars().first()
                if user_obj and user_obj.telegram_chat_id:
                    from app.core.bot import bot
                    if bot:
                        try:
                            # Extract intent from ai_analysis if available
                            ai_analysis: Dict[str, Any] = note.ai_analysis or {}
                            intent: str = ai_analysis.get("intent", "note")
                            
                            safe_title: str = escape_markdown(note.title or "Untitled")
                            safe_intent: str = escape_markdown(intent)
                            
                            msg: str = f"✅ **Saved!**\nTitle: {safe_title}\nIntent: {safe_intent}"
                            
                            # Character limit check (4096 is absolute, 4000 is safe)
                            if len(msg) > 4000:
                                msg = msg[:3980] + "..."
                                
                            await bot.send_message(chat_id=user_obj.telegram_chat_id, text=msg, parse_mode="Markdown")
                            logger.info(f"Sent TG notification to user {user_obj.id}")
                        except Exception as tg_err:
                            logger.warning(f"Failed to send TG notification: {tg_err}")

                # 6. Web Push Notification
                if user_obj and user_obj.push_subscriptions:
                    try:
                        from pywebpush import webpush, WebPushException
                        from app.core.config import settings
                        import json
                        
                        if settings.VAPID_PRIVATE_KEY:
                            payload: str = json.dumps({
                                "title": "Note Processed",
                                "body": f"{note.title or 'Audio Note'} has been analyzed.",
                                "icon": "/logo.png",
                                "url": f"/dashboard?note={note.id}"
                            })
                            
                            # push_subscriptions is a list of dicts
                            for sub in (user_obj.push_subscriptions or []):
                                try:
                                    webpush(
                                        subscription_info=sub,
                                        data=payload,
                                        vapid_private_key=settings.VAPID_PRIVATE_KEY,
                                        vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL}
                                    )
                                except WebPushException as ex:
                                    logger.warning(f"Push failed for subscription: {ex}")
                                except Exception as ex:
                                    logger.warning(f"Push generic error: {ex}")
                            
                            logger.info(f"Sent Push notifications to user {user_obj.id}")
                    except Exception as push_err:
                        logger.warning(f"Failed to send Push notification: {push_err}")
    except Exception as e:
        logger.error(f"Error processing note {note_id}: {e}")
        # Failure Recovery Transaction
        try:
             async with AsyncSessionLocal() as db_err:
                result = await db_err.execute(select(Note).where(Note.id == note_id))
                note_err: Optional[Note] = result.scalars().first()
                
                if note_err:
                    note_err.status = "FAILED"
                    note_err.processing_error = str(e)
                    
                    # Refund User Quota
                    estimated: int = note_err.duration_seconds or 0
                    if estimated > 0:
                        res_u = await db_err.execute(select(User).where(User.id == note_err.user_id))
                        u_err: Optional[User] = res_u.scalars().first()
                        if u_err:
                            u_err.monthly_usage_seconds = max(0, u_err.monthly_usage_seconds - estimated)
                            logger.info(f"Refunded {estimated}s to user {u_err.id} due to failure.")
                    
                    await db_err.commit()
                    logger.info(f"Marked note {note_id} as FAILED and refunded quota.")
                    
        except Exception as db_e:
            logger.critical(f"Critical DB Error during failure handling: {db_e}")
    finally:
        await db.close()

@celery.task(name="process_note")
def process_note_task(note_id: str) -> Dict[str, str]:
    """Background task to process a new note."""
    async_to_sync(_process_note_async)(note_id)
    return {"status": "success", "note_id": note_id}

@celery.task(name="cluster_notes")
def cluster_notes_task(user_id: str) -> Dict[str, str]:
    """Cluster user notes based on embeddings."""
    async_to_sync(_cluster_notes_async)(user_id)
    return {"status": "success", "user_id": user_id}

async def _cluster_notes_async(user_id: str) -> None:
    logger.info(f"Starting topic clustering for user: {user_id}")
    db: AsyncSession = AsyncSessionLocal()
    try:
        # 1. Fetch notes
        result = await db.execute(select(Note).join(NoteEmbedding).where(
            Note.user_id == user_id,
            Note.status == 'COMPLETED'
        ))
        notes: List[Note] = list(result.scalars().all())
        
        if len(notes) < 3:
            logger.info(f"Not enough notes ({len(notes)}) to cluster for user {user_id}")
            return

        # 2. Extract Embeddings
        import numpy as np
        embeddings: List[List[float]] = [n.embedding_data.embedding for n in notes if n.embedding_data]
        
        if not embeddings: 
            logger.warning(f"No embeddings found for user {user_id} notes")
            return

        X = np.array(embeddings)
        
        # 3. K-Means
        from sklearn.cluster import KMeans
        n_clusters: int = max(2, min(5, len(notes) // 2))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(X)
        labels: np.ndarray = kmeans.labels_
        
        # 4. Update
        for i, note in enumerate(notes):
            note.cluster_id = f"topic_{labels[i]}"
        
        await db.commit()
        logger.info(f"Clustered {len(notes)} notes into {n_clusters} topics.")
        
    except Exception as e:
        logger.error(f"Clustering Error for user {user_id}: {e}")
    finally:
        await db.close()

@celery.task(name="cleanup_old_notes")
def cleanup_old_notes_task() -> Dict[str, str]:
    """Periodic task to delete old notes."""
    async_to_sync(_cleanup_old_notes_async)()
    return {"status": "cleanup_started"}

async def _cleanup_old_notes_async() -> None:
    from datetime import datetime, timedelta, timezone
    
    logger.info("Starting retention cleanup...")
    db: AsyncSession = AsyncSessionLocal()
    try:
        now: datetime = datetime.now(timezone.utc)
        cutoff_free: datetime = now - timedelta(days=90)
        cutoff_pro: datetime = now - timedelta(days=365)
        
        # Helper to delete list
        async def delete_batch(notes: List[Note]) -> int:
            count: int = 0
            for note in notes:
                key: Optional[str] = note.storage_key
                if not key and note.audio_url and "amazonaws.com" in note.audio_url:
                    try:
                        key = os.path.basename(urlparse(note.audio_url).path)
                    except Exception:
                        key = None
                
                if key:
                    try:
                        await storage_client.delete_file(key)
                    except Exception as s3_err:
                        logger.warning(f"Failed to delete file {key} from storage: {s3_err}")

                await db.delete(note)
                count += 1
            return count

        # Free
        res_free = await db.execute(select(Note).join(User).where(User.tier == UserTier.FREE, Note.created_at < cutoff_free))
        c_free: int = await delete_batch(list(res_free.scalars().all()))
        
        # Pro
        res_pro = await db.execute(select(Note).join(User).where(User.tier == UserTier.PRO, Note.created_at < cutoff_pro))
        c_pro: int = await delete_batch(list(res_pro.scalars().all()))

        await db.commit()
        logger.info(f"Cleanup complete. Deleted {c_free} Free and {c_pro} Pro notes.")
            
    except Exception as e:
        logger.error(f"Cleanup Error: {e}")
    finally:
        await db.close()

@celery.task(name="check_subscription_expiry")
def check_subscription_expiry_task() -> Dict[str, str]:
    """Daily check for subscription expiry."""
    async_to_sync(_check_subscription_expiry_async)()
    return {"status": "expiry_check_started"}

async def _check_subscription_expiry_async() -> None:
    from datetime import datetime, timedelta, timezone
    from app.services.email import send_email
    
    logger.info("Starting subscription expiry check...")
    db: AsyncSession = AsyncSessionLocal()
    try:
        # Fetch all Pro/Premium users
        result = await db.execute(select(User).where(User.tier.in_([UserTier.PRO, UserTier.PREMIUM])))
        users: List[User] = list(result.scalars().all())
        
        now: datetime = datetime.now(timezone.utc)
        
        notified_count: int = 0
        
        for user in users:
            if not user.billing_cycle_start:
                continue
                
            # Calculate Next Renewal
            cycle_start: datetime = user.billing_cycle_start.replace(tzinfo=timezone.utc) if user.billing_cycle_start.tzinfo is None else user.billing_cycle_start
            
            is_yearly: bool = user.billing_period == 'yearly'
            period: timedelta = timedelta(days=365) if is_yearly else timedelta(days=30)
            
            # Move cycle_start to future if it's in the past
            renewal_date: datetime = cycle_start
            while renewal_date < now:
                renewal_date += period
                
            time_until: timedelta = renewal_date - now
            
            if time_until.days == 3:
                # Saved Time Calculation (Approx)
                saved_hours: int = int(((user.monthly_usage_seconds or 0) * 3) / 3600)
                
                if getattr(user, 'cancel_at_period_end', False):
                    # CANCELLATION NOTICE
                    subject: str = f"Your VoiceBrain Access Ends in 3 Days"
                    body: str = f"""
                    <h1>Subscription Ending Soon</h1>
                    <p>Hi {user.full_name or 'there'},</p>
                    <p>This is a reminder that your <b>{user.tier.capitalize()}</b> subscription is set to expire on {renewal_date.strftime('%B %d, %Y')} and will <b>NOT</b> renew.</p>
                    <p>You've saved roughly <b>{saved_hours} hours</b> this month.</p>
                    <p>If you changed your mind and want to keep your access, you can resume your subscription below.</p>
                    <p><a href="https://voicebrain.ai/settings">Resume Subscription</a></p>
                    <br>
                    <p>Best,<br>The VoiceBrain Team</p>
                    """
                    logger.info(f"Sent cancellation warning to {user.email}")
                else:
                    # RENEWAL NOTICE
                    subject = f"VoiceBrain {user.tier.capitalize()} Renews in 3 Days"
                    body = f"""
                    <h1>Your Subscription is Renewing Soon</h1>
                    <p>Hi {user.full_name or 'there'},</p>
                    <p>This is a friendly reminder that your <b>{user.tier.capitalize()}</b> plan will renew on {renewal_date.strftime('%B %d, %Y')}.</p>
                    <p>You've been productive! You saved approximately <b>{saved_hours} hours</b> this month using VoiceBrain.</p>
                    <p>Please ensure your payment method is up to date.</p>
                    <p><a href="https://voicebrain.ai/settings">Manage Subscription</a></p>
                    <br>
                    <p>Best,<br>The VoiceBrain Team</p>
                    """
                    logger.info(f"Sent renewal notification to {user.email}")
                
                try:
                    await send_email(user.email, subject, body)
                    notified_count += 1
                except Exception as email_err:
                    logger.error(f"Failed to send expiry email to {user.email}: {email_err}")
        
        logger.info(f"Expiry check complete. Sent {notified_count} notifications.")
            
    except Exception as e:
        logger.error(f"Expiry Check Error: {e}")
    finally:
        await db.close()
@celery.task(name="backup_database")
def backup_database_task() -> Dict[str, str]:
    """Daily database backup to S3."""
    async_to_sync(_backup_database_async)()
    return {"status": "backup_started"}

async def _backup_database_async() -> None:
    from datetime import datetime, timezone
    import gzip
    
    logger.info("Starting database backup...")
    
    # 1. Config
    pg_user: str = os.getenv("POSTGRES_USER", "postgres")
    pg_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    pg_host: str = os.getenv("POSTGRES_HOST", "db")
    pg_port: str = os.getenv("POSTGRES_PORT", "5432")
    pg_db: str = os.getenv("POSTGRES_DB", "voicebrain")
    
    # TIMESTAMP
    now: datetime = datetime.now(timezone.utc)
    timestamp: str = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename: str = f"voicebrain_db_{timestamp}.sql.gz"
    backup_path: str = f"/tmp/{filename}"
    
    # 2. Dump
    env: Dict[str, str] = os.environ.copy()
    env["PGPASSWORD"] = pg_password
    
    try:
        with gzip.open(backup_path, 'wb') as f_out:
            cmd: List[str] = ['pg_dump', '-h', pg_host, '-p', pg_port, '-U', pg_user, pg_db]
            proc: subprocess.CompletedProcess = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if proc.returncode != 0:
                logger.error(f"pg_dump failed: {proc.stderr.decode()}")
                return

            f_out.write(proc.stdout)
            
        logger.info(f"Database dumped to {backup_path}, size: {os.path.getsize(backup_path)} bytes")
        
        # 3. Upload to S3
        s3_key: str = f"backups/{filename}"
        with open(backup_path, "rb") as f_in:
             await storage_client.upload_file(f_in, s3_key, content_type="application/gzip")
             
        logger.info(f"Backup uploaded to {s3_key}")
        
        # 4. Prune Old Backups (Keep 7 days)
        if hasattr(storage_client, 'is_mock') and not storage_client.is_mock and hasattr(storage_client, 's3_client'):
             try:
                s3: Any = storage_client.s3_client
                bucket: str = os.getenv("S3_BUCKET_NAME", "voicebrain-audio-dev")
                
                # List objects in backups/
                objs = s3.list_objects_v2(Bucket=bucket, Prefix="backups/")
                if 'Contents' in objs:
                    backups = sorted(objs['Contents'], key=lambda x: x['LastModified'])
                    
                    # Keep last 7
                    if len(backups) > 7:
                        to_delete = backups[:len(backups)-7]
                        for obj in to_delete:
                            logger.info(f"Pruning old backup: {obj['Key']}")
                            s3.delete_object(Bucket=bucket, Key=obj['Key'])
             except Exception as prune_err:
                  logger.warning(f"Pruning failed: {prune_err}")

    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Backup subprocess/OS failure: {e}")
    except Exception as e:
        logger.error(f"Backup overall failure: {e}")
    finally:
        if os.path.exists(backup_path):
            try: os.remove(backup_path)
            except Exception as rm_e: logger.debug(f"Failed to remove backup file: {rm_e}")
@celery.task(name="generate_weekly_review")
def generate_weekly_review_task() -> Dict[str, str]:
    """Generates weekly coaching review for users."""
    async_to_sync(_generate_weekly_review_async)()
    return {"status": "reviews_generated"}

async def _generate_weekly_review_async() -> None:
    from datetime import datetime, timedelta, timezone
    
    logger.info("Starting weekly review generation...")
    db: AsyncSession = AsyncSessionLocal()
    http_client.start()
    try:
        # 1. Fetch Users
        now: datetime = datetime.now(timezone.utc)
        seven_days_ago: datetime = now - timedelta(days=7)
        
        active_users_res = await db.execute(
            select(Note.user_id).where(Note.created_at >= seven_days_ago).distinct()
        )
        active_user_ids: List[Optional[str]] = list(active_users_res.scalars().all())
        
        if not active_user_ids:
            logger.info("No active users found for weekly review.")
            return

        logger.info(f"Generating reviews for {len(active_user_ids)} users.")

        for user_id in active_user_ids:
            if not user_id: continue 
            
            # Fetch User's Notes
            notes_res = await db.execute(select(Note).where(
                Note.user_id == user_id,
                Note.created_at >= seven_days_ago,
                Note.status == 'COMPLETED'
            ))
            notes: List[Note] = list(notes_res.scalars().all())
            
            if not notes or len(notes) < 3:
                 continue

            # Fetch User
            u_res = await db.execute(select(User).where(User.id == user_id))
            user_obj: Optional[User] = u_res.scalars().first()
            if not user_obj: continue

            target_lang: str = user_obj.target_language or "Original"

            summaries: List[str] = [f"- {n.title}: {n.summary} (Mood: {n.mood})" for n in notes if n.summary]
            context_str: str = "\n".join(summaries)
            
            # AI Analysis
            review_text: str = await ai_service.analyze_weekly_notes(context_str, target_language=target_lang)
            
            # Create System Note
            title: str = f"Weekly Review: {seven_days_ago.strftime('%b %d')} - {now.strftime('%b %d')}"
            
            review_note = Note(
                user_id=user_id,
                title=title,
                transcription_text="System Generated Review based on your weekly activity.",
                summary=review_text,
                tags=["Weekly Review", "System"],
                mood="Coaching",
                status="COMPLETED",
                processing_step="Completed",
                duration_seconds=0,
                created_at=now,
                is_audio_note=False
            )
            db.add(review_note)
            
            # Delivery: Telegram
            if user_obj.telegram_chat_id:
                 from app.core.bot import bot
                 if bot:
                     msg: str = f"📅 **{title}**\n\n{review_text[:200]}...\n\n[Read Full Review](https://voicebrain.app/dashboard)"
                     try:
                         await bot.send_message(chat_id=user_obj.telegram_chat_id, text=msg, parse_mode="Markdown")
                     except Exception as tg_e:
                         logger.warning(f"TG Weekly fail for {user_id}: {tg_e}")
                         
            # Delivery: Email
            if user_obj.email:
                try:
                    from app.services.email import send_email 
                    import markdown
                    
                    html_content: str = markdown.markdown(review_text)
                    email_body: str = f"""
                    <h1>{title}</h1>
                    <p>Hi {user_obj.full_name or 'there'},</p>
                    <p>Here is your AI-generated weekly review based on your notes.</p>
                    <hr>
                    {html_content}
                    <hr>
                    <p><a href="https://voicebrain.app/dashboard">View in Dashboard</a></p>
                    """
                    await send_email(user_obj.email, title, email_body)
                except Exception as email_e:
                    logger.warning(f"Email Weekly fail for {user_id}: {email_e}")
        
        await db.commit()
        logger.info("Weekly reviews generated successfully.")

    except Exception as e:
        logger.error(f"Weekly Review Generation Error: {e}")
    finally:
        await db.close()
