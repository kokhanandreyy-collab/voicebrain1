import logging
import io
import uuid
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandObject, Command
from aiogram.types import Message
from sqlalchemy.future import select
from infrastructure.config import settings
from app.core.bot import bot
from infrastructure.database import AsyncSessionLocal
from app.models import User, Note
from infrastructure.storage import storage_client
from workers.transcribe_tasks import process_transcribe

logger = logging.getLogger(__name__)

# Initialize dispatcher
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("👋 Welcome to VoiceBrain! To connect your account, please use the link from your Settings page or use `/start <your_api_key>`.")
        return

    api_key = command.args
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.api_key == api_key))
        user = result.scalars().first()
        
        if not user:
            await message.answer("❌ Invalid API Key. Please check your settings.")
            return
            
        user.telegram_chat_id = str(message.chat.id)
        await db.commit()
        await message.answer(f"✅ Awesome, {user.email}! Your account is now linked. You can send me voice messages and I'll process them.")

@dp.message(F.voice)
async def handle_voice(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == str(message.chat.id)))
        user = result.scalars().first()
        
        if not user:
            await message.answer("⚠️ Your account is not linked. Use `/start <api_key>` to link it.")
            return

        # 1. Download from Telegram
        await message.answer("🧠 Listening...")
        
        voice = message.voice
        if voice.file_size > 20 * 1024 * 1024:
            await message.answer("❌ Voice message is too large (max 20MB).")
            return

        file = await bot.get_file(voice.file_id)
        file_path = file.file_path
        
        # Download to memory
        voice_data = io.BytesIO()
        await bot.download_file(file_path, voice_data)
        voice_data.seek(0)

        # 2. Upload to S3
        file_ext = "ogg" # Telegram voice is usually OGG/Opus
        file_key = f"{user.id}/tg_{uuid.uuid4()}.{file_ext}"
        
        try:
            audio_url = await storage_client.upload_file(
                voice_data, 
                file_key, 
                content_type="audio/ogg"
            )
        except Exception as e:
            logger.error(f"S3 Upload failed for TG voice: {e}")
            await message.answer("❌ Failed to save voice message. Please try again later.")
            return

        # 3. Create Note (Processing State)
        duration_est = voice.duration
        
        new_note = Note(
            user_id=user.id,
            audio_url=audio_url,
            storage_key=file_key,
            title="Telegram Note...",
            status="PROCESSING",
            duration_seconds=duration_est,
            summary="Processing voice from Telegram...",
            transcription_text=""
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)

        # 4. Trigger Worker
        process_transcribe.delay(new_note.id)
        
        # We don't reply more here, the worker will send a follow-up if telegram_chat_id is set.
        
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    """Handle text messages (e.g. replies to clarification questions)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == str(message.chat.id)))
        user = result.scalars().first()
        if not user:
            await message.answer("⚠️ Not linked.")
            return

        text_content = message.text
        # If this is a reply to the bot, we prepend the bot's message as context
        if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
            original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
            text_content = f"Question: {original_text}\nAnswer: {message.text}"

        # Create Text Note
        new_note = Note(
            user_id=user.id,
            title="Clarification/Text",
            status="PROCESSING",
            transcription_text=text_content,
            is_audio_note=False,
            summary="Processing response..."
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)

        # Trigger pipeline
        from workers.analyze_tasks import process_analyze
        process_analyze.delay(new_note.id)
        
        await message.answer("📝 Learning from your response...")

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == str(message.chat.id)))
        user = result.scalars().first()
        if not user:
            await message.answer("⚠️ Not linked.")
            return

        flags = user.feature_flags or {}
        text = "⚙️ *Feature Flags:*\n"
        for k, v in flags.items():
            status = "✅" if v else "❌"
            text += f"{status} `{k}`\n"
        
        text += "\nUse `/toggle <flag_name>` to switch."
        await message.answer(text, parse_mode="Markdown")

@dp.message(Command("toggle"))
async def cmd_toggle(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: `/toggle <flag_name>`")
        return

    key = command.args.strip()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == str(message.chat.id)))
        user = result.scalars().first()
        if not user:
            return

        flags = dict(user.feature_flags or {})
        current = flags.get(key, False) # Default to False if not present? Or True? Request said default mostly True.
        # If key doesn't exist, maybe we shouldn't toggle it? 
        # But for "notion_enabled" it effectively defaults to True if checked cleanly, 
        # but here we are explicit. 
        # Let's assume if it's missing, we set it to False (disable) because we are toggling FROM default?
        # Creating a new flag.
        
        flags[key] = not current
        user.feature_flags = flags
        await db.commit()
        
        status = "Enabled" if flags[key] else "Disabled"
        await message.answer(f"✅ {key} is now *{status}*.", parse_mode="Markdown")

async def start_bot():
    if not bot:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram Bot will not start.")
        return
    logger.info("Starting Telegram Bot...")
    await dp.start_polling(bot)
