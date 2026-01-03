import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Load env from root or backend
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (chat_id TEXT PRIMARY KEY, api_key TEXT)''')
    conn.commit()
    conn.close()

def get_api_key(chat_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT api_key FROM users WHERE chat_id=?", (str(chat_id),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_api_key(chat_id: int, api_key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (chat_id, api_key) VALUES (?, ?)", (str(chat_id), api_key))
    conn.commit()
    conn.close()

# Initialize Bot and Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    init_db()
    logger.info("Database initialized.")

    # Import handlers here to avoid circular imports
    from telegram.handlers import chat, voice, clarification
    
    dp.include_router(chat.router)
    dp.include_router(voice.router)
    dp.include_router(clarification.router)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
