from aiogram import Bot
from app.infrastructure.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else None
