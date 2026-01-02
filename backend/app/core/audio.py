import asyncio
import os
import shutil
import tempfile
import subprocess
from typing import Tuple
from loguru import logger
from app.services.ai_service import ai_service
from infrastructure.storage import storage_client
from app.models import Note

class AudioProcessor:
    async def process_audio(self, note: Note) -> Tuple[str, int]:
        """Orchestrates download, optimization, and transcription."""
        
        # 1. Download
        content = await self.download_audio(note)
        
        # 2. Optimize
        content = await self.remove_silence(content)
        
        # 3. Transcribe
        text, duration = await self.transcribe(content)
        
        return text, duration

    async def download_audio(self, note: Note) -> bytes:
        if note.storage_key:
            return await storage_client.read_file(note.storage_key)
        
        # Fallback logic omitted for brevity in core, or keep if crucial
        # Assuming storage_key is primary now.
        if note.audio_url:
             # Logic to extract key from url if possible or generic read
             # Simplifying for "Clean Architecture" unless needed
             pass
        raise ValueError(f"No storage key for note {note.id}")

    async def remove_silence(self, content: bytes) -> bytes:
        """Use FFmpeg to remove silence > 1s from audio."""
        if not shutil.which('ffmpeg'):
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
            await proc.communicate()

            if proc.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 0:
                    with open(output_path, "rb") as f_out:
                        return f_out.read()
            return content
        except Exception:
            return content
        finally:
            if os.path.exists(input_path): os.remove(input_path)
            if os.path.exists(output_path): os.remove(output_path)

    async def transcribe(self, content: bytes) -> Tuple[str, int]:
        # Calculate duration
        real_duration_sec = 0
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
                    val = stdout.decode().strip()
                    if val and val != "N/A":
                        real_duration_sec = int(float(val))
        except Exception:
            pass
        finally:
             if os.path.exists(tmp_path): os.remove(tmp_path)

        transcription = await ai_service.transcribe_audio(content)
        return transcription["text"], real_duration_sec

audio_processor = AudioProcessor()
