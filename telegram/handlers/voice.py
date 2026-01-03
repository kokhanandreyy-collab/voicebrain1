import httpx
import io
import uuid
from aiogram import Router, F, types
from telegram.bot import get_api_key, API_BASE_URL, logger, bot

router = Router()

@router.message(F.voice)
async def handle_voice(message: types.Message):
    api_key = get_api_key(message.chat.id)
    if not api_key:
        await message.answer("⚠️ Your account is not linked. Use `/start <api_key>` to link it.")
        return

    await message.answer("🧠 Downloading...")

    voice = message.voice
    if voice.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Voice message is too large (max 20MB).")
        return

    try:
        # Download from Telegram
        file = await bot.get_file(voice.file_id)
        voice_data = await bot.download_file(file.file_path)
        
        # Prepare for upload
        await message.bot.send_chat_action(message.chat.id, "upload_voice")
        files = {
            'file': (f"tg_{uuid.uuid4()}.ogg", voice_data.getvalue(), 'audio/ogg')
        }

        await message.answer("✨ Processing your note...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/notes/upload",
                files=files,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0
            )

            if response.status_code == 200:
                data = response.json()
                note_id = data.get("id")
                # The backend handles transcription & analysis asynchronously.
                # We show a success message.
                await message.answer(
                    f"✅ **Note captured!**\n"
                    f"I'm analyzing your voice now. I'll send you a summary shortly if clarification is needed.",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(f"❌ Upload failed: {response.text}")

    except Exception as e:
        logger.error(f"Voice Processing Error: {e}")
        await message.answer("❌ Failed to process voice message.")
