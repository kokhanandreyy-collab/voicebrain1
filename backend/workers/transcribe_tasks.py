import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional
from urllib.parse import urlparse

from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User
from app.core.database import AsyncSessionLocal
from app.core.storage import storage_client

# Successor Task (will be imported locally to avoid circular)
# from workers.analyze_tasks import process_analyze

async def step_download_audio(note: Note) -> bytes:
    """Download audio content from storage."""
    if note.storage_key:
        try:
            return await storage_client.read_file(note.storage_key)
        except Exception as e:
            logger.error(f"Failed to read file from storage key {note.storage_key}: {e}")
            raise

    if note.audio_url:
        try:
            path = urlparse(note.audio_url).path
            key = os.path.basename(path)
            if key:
                logger.info(f"Attempting fallback download with key: {key}")
                return await storage_client.read_file(key)
        except Exception as e:
            logger.warning(f"Fallback download failed: {e}")

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
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-af', 'silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-30dB',
            '-c:a', 'libopus',
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
                logger.info(f"Silence removal successful. Size: {len(content)/1024:.1f}KB -> {file_size/1024:.1f}KB")
                return optimized_content
        return content
    except Exception as e:
        logger.error(f"Silence removal error: {e}")
        return content
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p): os.remove(p)

async def step_transcribe(content: bytes) -> Tuple[str, int]:
    """Transcribe audio and calculate precise duration."""
    real_duration_sec: int = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        if shutil.which('ffprobe'):
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', tmp_path
            ]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode == 0:
                output_val = stdout.decode().strip()
                if output_val and output_val != 'N/A':
                    real_duration_sec = int(float(output_val))
    except Exception as probe_err:
        logger.warning(f"Duration analysis failed: {probe_err}")
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

    transcription = await ai_service.transcribe_audio(content)
    return transcription["text"], real_duration_sec

async def _process_transcribe_async(note_id: str) -> None:
    logger.info(f"[Transcribe] Processing note: {note_id}")
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return

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
            user_res = await db.execute(select(User).where(User.id == note.user_id))
            user = user_res.scalars().first()
            if user:
                diff = duration - est
                user.monthly_usage_seconds = max(0, user.monthly_usage_seconds + diff)
        
        note.processing_step = "🧠 Extracting action items..."
        await db.commit()
        
        # Trigger Next Stage
        from workers.analyze_tasks import process_analyze
        process_analyze.delay(note_id)
        
    except Exception as e:
        logger.error(f"Transcribe task failed for {note_id}: {e}")
        from workers.common_tasks import handle_note_failure
        await handle_note_failure(note_id, str(e))
    finally:
        await db.close()

@celery.task(name="transcribe.process_note")
def process_transcribe(note_id: str):
    async_to_sync(_process_transcribe_async)(note_id)
    return {"status": "transcribed", "note_id": note_id}
