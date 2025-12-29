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

# Local
# Local
from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, Integration, User, IntegrationLog, NoteEmbedding, UserTier
from app.core.database import AsyncSessionLocal
from app.core.storage import storage_client
from app.services.integrations import get_integration_handler
from app.core.http_client import http_client 

# Configure Logging
logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown V1."""
    if not text:
        return ""
    # Characters to escape in Markdown V1: _ * [ `
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f'\\{char}')
    return text

async def step_download_audio(note: Note, db) -> bytes:
    """Download audio content from storage."""
    # 1. Primary: Storage Key
    if note.storage_key:
        return await storage_client.read_file(note.storage_key)

    # 2. Fallback: Parse from URL (if legacy data exists)
    if note.audio_url:
        try:
            path = urlparse(note.audio_url).path
            key = os.path.basename(path) # clearer than split
            if key:
                logger.info(f"Attempting fallback download with key: {key}")
                return await storage_client.read_file(key)
        except Exception as e:
            logger.warning(f"Fallback key extraction failed: {e}")

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
        # silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-30dB
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-af', 'silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-30dB',
            '-c:a', 'libopus', # Re-encode to opus/webm
            output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate() # No timeout for optimization, or maybe generous one

        if proc.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                async with asyncio.Lock(): # Not needed for simple file read but good practice if async file I/O 
                    # Re-reading blocking I/O is okay in worker thread usually, but use simple read
                    with open(output_path, "rb") as f_out:
                         optimized_content = f_out.read()
                
                original_size = len(content)
                savings = (1 - (file_size / original_size)) * 100
                logger.info(f"Silence removal successful. Size reduced by {savings:.1f}% ({original_size/1024:.1f}KB -> {file_size/1024:.1f}KB)")
                return optimized_content
            else:
                 logger.warning("FFmpeg produced empty file")
        else:
            logger.warning(f"FFmpeg failed: {stderr.decode()}")
            
        return content
    except Exception as e:
        logger.error(f"Silence removal exception: {e}")
        return content
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

async def step_transcribe(content: bytes) -> tuple[str, int]:
    """Transcribe audio and calculate precise duration."""
    real_duration_sec = 0
    
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
                        logger.warning(f"FFprobe non-zero exit: {stderr.decode()}")
                else:
                    logger.warning(f"FFprobe failed: {stderr.decode()}")

            except asyncio.TimeoutError:
                logger.warning("FFProbe timed out, killing...")
                try:
                    proc.kill()
                    await proc.wait()
                except: pass
    except Exception as probe_err:
        logger.warning(f"Duration analysis failed: {probe_err}")
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

    transcription = await ai_service.transcribe_audio(content)
    text = transcription["text"]
    return text, real_duration_sec

async def step_analyze(text: str, user_context: str = None, target_language: str = "Original") -> dict:
    """Analyze text using AI service."""
    return await ai_service.analyze_text(text, user_context=user_context, target_language=target_language)

async def step_embed_and_save(note: Note, text: str, analysis: dict, db):
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
    note.ai_analysis = {
        "intent": analysis.get("intent", "note"),
        "suggested_project": analysis.get("suggested_project", "Inbox"),
        "entities": analysis.get("entities", []),
        "priority": analysis.get("priority", 4),
        "notion_properties": analysis.get("notion_properties", {}),
        "explicit_destination_app": analysis.get("explicit_destination_app"),
        "explicit_folder": analysis.get("explicit_folder")
    }
    
    # Embedding
    search_content = f"{note.title} {note.summary} {text} {' '.join(note.tags)}"
    embedding_vector = await ai_service.generate_embedding(search_content)
    
    note_embedding = NoteEmbedding(note_id=note.id, embedding=embedding_vector)
    db.add(note_embedding)

async def step_sync_integrations(note: Note, db):
    """Sync processed note with enabled integrations."""
    # 1. Check for Explicit Routing
    explicit_app = (note.ai_analysis or {}).get("explicit_destination_app")
    
    int_result = await db.execute(select(Integration).where(
        Integration.user_id == note.user_id
    ).options(selectinload(Integration.user)))
    user_integrations = int_result.scalars().all()

    # If explicit app specified, filter to only that one
    if explicit_app:
        user_integrations = [i for i in user_integrations if i.provider == explicit_app]
        logger.info(f"Explicit Routing detected. Syncing ONLY to: {explicit_app}")

    for integration in user_integrations:
        handler = get_integration_handler(integration.provider)
        if handler:
            status_log = "SUCCESS"
            error_msg = None
            try:
                # Inspect if handler.sync accepts 'db'
                sig = inspect.signature(handler.sync)
                if 'db' in sig.parameters:
                      await handler.sync(integration, note, db=db)
                else:
                      await handler.sync(integration, note)
            except Exception as int_err:
                logger.error(f"Integration failed {integration.provider}: {int_err}")
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

async def _process_note_async(note_id: str):
    logger.info(f"Starting processing for note: {note_id}")
    
    # Ensure client is started (idempotent)
    http_client.start()
    
    db = AsyncSessionLocal()
    try:
            # 1. Fetch Note
            result = await db.execute(select(Note).where(Note.id == note_id))
            note = result.scalars().first()
            if not note:
                logger.error(f"Note {note_id} not found")
                return
            
            # Capture estimated duration (already deducted by API)
            estimated_duration = note.duration_seconds or 0
            
            # --- Pipeline execution ---
            note.processing_step = "☁️ Uploading..."
            await db.commit()
            
            content = await step_download_audio(note, db)
            
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
                user_record = user_result.scalars().first()
                if user_record:
                    diff = real_duration_sec - estimated_duration
                    user_record.monthly_usage_seconds = max(0, user_record.monthly_usage_seconds + diff)
                    logger.info(f"Quota adjusted: {diff:+d}s")

            # Intermediate commit for progressive rendering
            note.transcription_text = text
            note.processing_step = "🧠 Extracting action items..."
            await db.commit()
            
            # Fetch User Bio & Lang
            user_bio = None
            target_lang = "Original"
            if note.user_id:
                # We could have fetched user with note earlier, but simple query is fine
                u_res = await db.execute(select(User).where(User.id == note.user_id))
                u = u_res.scalars().first()
                if u:
                    if u.bio: user_bio = u.bio
                    if u.target_language: target_lang = u.target_language

            analysis = await step_analyze(text, user_context=user_bio, target_language=target_lang)
            
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
            if note.status == "COMPLETED":
                user_res = await db.execute(select(User).where(User.id == note.user_id))
                user_obj = user_res.scalars().first()
                if user_obj and user_obj.telegram_chat_id:
                    from app.core.bot import bot
                    if bot:
                        try:
                            # Extract intent from ai_analysis if available
                            intent = note.ai_analysis.get("intent", "note") if note.ai_analysis else "note"
                            
                            safe_title = escape_markdown(note.title or "Untitled")
                            safe_intent = escape_markdown(intent)
                            
                            msg = f"✅ **Saved!**\nTitle: {safe_title}\nIntent: {safe_intent}"
                            
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
                            payload = json.dumps({
                                "title": "Note Processed",
                                "body": f"{note.title or 'Audio Note'} has been analyzed.",
                                "icon": "/logo.png",
                                "url": f"/dashboard?note={note.id}"
                            })
                            
                            # push_subscriptions is a list of dicts
                            for sub in user_obj.push_subscriptions:
                                try:
                                    webpush(
                                        subscription_info=sub,
                                        data=payload,
                                        vapid_private_key=settings.VAPID_PRIVATE_KEY,
                                        vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL}
                                    )
                                except WebPushException as ex:
                                    logger.warning(f"Push failed for subscription: {ex}")
                                    # Potential TODO: Remove invalid subscription from DB
                                except Exception as ex:
                                    logger.warning(f"Push generic error: {ex}")
                            
                            logger.info(f"Sent Push notifications to user {user_obj.id}")
                    except Exception as push_err:
                        logger.warning(f"Failed to send Push notification: {push_err}")
    except Exception as e:
        logger.error(f"Error processing note {note_id}: {e}")
        # Failure Recovery Transaction
        # Failure Recovery Transaction
        try:
             async with AsyncSessionLocal() as db_err:
                result = await db_err.execute(select(Note).where(Note.id == note_id))
                note_err = result.scalars().first()
                
                if note_err:
                    note_err.status = "FAILED"
                    note_err.processing_error = str(e)
                    
                    # Refund User Quota
                    estimated = note_err.duration_seconds or 0
                    if estimated > 0:
                        res_u = await db_err.execute(select(User).where(User.id == note_err.user_id))
                        u_err = res_u.scalars().first()
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
def process_note_task(note_id: str):
    """Background task to process a new note."""
    async_to_sync(_process_note_async)(note_id)
    return {"status": "success", "note_id": note_id}

@celery.task(name="cluster_notes")
def cluster_notes_task(user_id: str):
    """Cluster user notes based on embeddings."""
    async_to_sync(_cluster_notes_async)(user_id)
    return {"status": "success", "user_id": user_id}

async def _cluster_notes_async(user_id: str):
    logger.info(f"Starting topic clustering for user: {user_id}")
    db = AsyncSessionLocal()
    try:
        try:
            # 1. Fetch notes
            result = await db.execute(select(Note).join(NoteEmbedding).where(
                Note.user_id == user_id,
                Note.status == 'COMPLETED'
            ))
            notes = result.scalars().all()
            
            if len(notes) < 3:
                return

            # 2. Extract Embeddings
            import numpy as np
            embeddings = [n.embedding_data.embedding for n in notes if n.embedding_data]
            
            if not embeddings: return

            X = np.array(embeddings)
            
            # 3. K-Means
            from sklearn.cluster import KMeans
            n_clusters = max(2, min(5, len(notes) // 2))
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(X)
            labels = kmeans.labels_
            
            # 4. Update
            for i, note in enumerate(notes):
                note.cluster_id = f"topic_{labels[i]}"
            
            await db.commit()
            logger.info(f"Clustered {len(notes)} notes into {n_clusters} topics.")
            
        except Exception as e:
            logger.error(f"Clustering Error: {e}")
    finally:
        await db.close()

@celery.task(name="cleanup_old_notes")
def cleanup_old_notes_task():
    """Periodic task to delete old notes."""
    async_to_sync(_cleanup_old_notes_async)()
    return {"status": "cleanup_started"}

async def _cleanup_old_notes_async():
    from datetime import datetime, timedelta, timezone
    
    logger.info("Starting retention cleanup...")
    db = AsyncSessionLocal()
    try:
        try:
            now = datetime.now(timezone.utc)
            cutoff_free = now - timedelta(days=90)
            cutoff_pro = now - timedelta(days=365)
            
            # Helper to delete list
            async def delete_batch(notes, label):
                count = 0
                for note in notes:
                    key = note.storage_key
                    if not key and note.audio_url and "amazonaws.com" in note.audio_url:
                        key = os.path.basename(urlparse(note.audio_url).path)
                    
                    if key:
                        await storage_client.delete_file(key)
                    await db.delete(note)
                    count += 1
                return count

            # Free
            res_free = await db.execute(select(Note).join(User).where(User.tier == UserTier.FREE, Note.created_at < cutoff_free))
            c_free = await delete_batch(res_free.scalars().all(), "FREE")
            
            # Pro
            res_pro = await db.execute(select(Note).join(User).where(User.tier == UserTier.PRO, Note.created_at < cutoff_pro))
            c_pro = await delete_batch(res_pro.scalars().all(), "PRO")

            await db.commit()
            logger.info(f"Cleanup complete. Deleted {c_free} Free and {c_pro} Pro notes.")
            
        except Exception as e:
            logger.error(f"Cleanup Error: {e}")
    finally:
        await db.close()

@celery.task(name="check_subscription_expiry")
def check_subscription_expiry_task():
    """Daily check for subscription expiry."""
    async_to_sync(_check_subscription_expiry_async)()
    return {"status": "expiry_check_started"}

async def _check_subscription_expiry_async():
    from datetime import datetime, timedelta, timezone
    from app.services.email import send_email
    
    logger.info("Starting subscription expiry check...")
    db = AsyncSessionLocal()
    try:
        try:
            # Fetch all Pro/Premium users
            result = await db.execute(select(User).where(User.tier.in_([UserTier.PRO, UserTier.PREMIUM])))
            users = result.scalars().all()
            
            now = datetime.now(timezone.utc)
            notification_window = timedelta(days=3)
            
            notified_count = 0
            
            for user in users:
                if not user.billing_cycle_start:
                    continue
                    
                # Calculate Next Renewal
                cycle_start = user.billing_cycle_start.replace(tzinfo=timezone.utc) if user.billing_cycle_start.tzinfo is None else user.billing_cycle_start
                
                is_yearly = user.billing_period == 'yearly'
                period = timedelta(days=365) if is_yearly else timedelta(days=30)
                
                # Move cycle_start to future if it's in the past
                renewal_date = cycle_start
                while renewal_date < now:
                    renewal_date += period
                    
                # Check if exactly 3 days away (with some buffer for execution time)
                time_until = renewal_date - now
                
                # We want: 2 days < time_until <= 3 days (roughly)
                # Or just check days component
                if time_until.days == 3:
                     # Saved Time Calculation (Approx)
                    saved_hours = int(((user.monthly_usage_seconds or 0) * 3) / 3600)
                    
                    if getattr(user, 'cancel_at_period_end', False):
                        # CANCELLATION NOTICE
                        subject = f"Your VoiceBrain Access Ends in 3 Days"
                        body = f"""
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
                    
                    await send_email(user.email, subject, body)
                    notified_count += 1
            
            logger.info(f"Expiry check complete. Sent {notified_count} notifications.")
            
        except Exception as e:
            logger.error(f"Expiry Check Error: {e}")
    finally:
        await db.close()
@celery.task(name="backup_database")
def backup_database_task():
    """Daily database backup to S3."""
    async_to_sync(_backup_database_async)()
    return {"status": "backup_started"}

async def _backup_database_async():
    from datetime import datetime, timezone, timedelta
    import gzip
    
    logger.info("Starting database backup...")
    
    # 1. Config
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    pg_host = os.getenv("POSTGRES_HOST", "db")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "voicebrain")
    
    # TIMESTAMP
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"voicebrain_db_{timestamp}.sql.gz"
    backup_path = f"/tmp/{filename}"
    
    # 2. Dump
    # PGPASSWORD env var is safest way to pass password to pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password
    
    try:
        # Note: pg_dump must be installed in the worker container
        # If running locally without docker, ensure pg_dump is in PATH
        with gzip.open(backup_path, 'wb') as f_out:
            cmd = ['pg_dump', '-h', pg_host, '-p', pg_port, '-U', pg_user, pg_db]
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if proc.returncode != 0:
                logger.error(f"pg_dump failed: {proc.stderr.decode()}")
                return

            f_out.write(proc.stdout)
            
        logger.info(f"Database dumped to {backup_path}, size: {os.path.getsize(backup_path)} bytes")
        
        # 3. Upload to S3
        s3_key = f"backups/{filename}"
        with open(backup_path, "rb") as f_in:
             await storage_client.upload_file(f_in, s3_key, content_type="application/gzip")
             
        logger.info(f"Backup uploaded to {s3_key}")
        
        # 4. Prune Old Backups (Keep 7 days)
        # This requires list capability which StorageClient might expose or we use boto3 directly if accessible
        if not storage_client.is_mock and hasattr(storage_client, 's3_client'):
             try:
                s3 = storage_client.s3_client
                bucket = os.getenv("S3_BUCKET_NAME", "voicebrain-audio-dev")
                
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

    except Exception as e:
        logger.error(f"Backup failed: {e}")
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)
@celery.task(name="generate_weekly_review")
def generate_weekly_review_task():
    """Generates weekly coaching review for users."""
    async_to_sync(_generate_weekly_review_async)()
    return {"status": "reviews_generated"}

async def _generate_weekly_review_async():
    from datetime import datetime, timedelta, timezone
    
    logger.info("Starting weekly review generation...")
    db = AsyncSessionLocal()
    http_client.start()
    try:
        try:
            # 1. Fetch Users (Active only could be better, but let's do all for MVP)
            # Optimization: Only select users who have created notes in last 7 days.
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            
            # Subquery to find active user IDs
            active_users_res = await db.execute(
                select(Note.user_id).where(Note.created_at >= seven_days_ago).distinct()
            )
            active_user_ids = active_users_res.scalars().all()
            
            if not active_user_ids:
                logger.info("No active users found for weekly review.")
                return

            logger.info(f"Generating reviews for {len(active_user_ids)} users.")

            for user_id in active_user_ids:
                if not user_id: continue # Skip None
                
                # Fetch User's Notes from last 7 days
                notes_res = await db.execute(select(Note).where(
                    Note.user_id == user_id,
                    Note.created_at >= seven_days_ago,
                    Note.status == 'COMPLETED' # Only analyzed notes
                ))
                notes = notes_res.scalars().all()
                
                if not notes or len(notes) < 3:
                     # Skip if too few notes for meaningful review
                     continue

                # Prepare User & Context
                u_res = await db.execute(select(User).where(User.id == user_id))
                user_obj = u_res.scalars().first()
                if not user_obj: continue

                target_lang = user_obj.target_language or "Original"

                summaries = [f"- {n.title}: {n.summary} (Mood: {n.mood})" for n in notes if n.summary]
                context_str = "\n".join(summaries)
                
                # AI Analysis
                review_text = await ai_service.analyze_weekly_notes(context_str, target_language=target_lang)
                
                # Create System Note
                title = f"Weekly Review: {seven_days_ago.strftime('%b %d')} - {now.strftime('%b %d')}"
                
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
                         msg = f"📅 **{title}**\n\n{review_text[:200]}...\n\n[Read Full Review](https://voicebrain.app/dashboard)"
                         try:
                             await bot.send_message(chat_id=user_obj.telegram_chat_id, text=msg, parse_mode="Markdown")
                         except Exception as tg_e:
                             logger.warning(f"TG Weekly fail for {user_id}: {tg_e}")
                             
                # Delivery: Email
                if user_obj.email:
                    try:
                        from app.services.email import send_email # Local import to avoid circular dep if any
                        import markdown
                        
                        html_content = markdown.markdown(review_text)
                        email_body = f"""
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
