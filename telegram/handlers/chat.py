import httpx
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.bot import get_api_key, set_api_key, API_BASE_URL, logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if command.args:
        api_key = command.args
        set_api_key(message.chat.id, api_key)
        await message.answer(
            f"✅ **Account linked!**\n\n"
            "You can now send voice notes to record them or just talk to me using 'Ask AI' mode.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "👋 **Welcome to VoiceBrain!**\n\n"
            "To get started, please link your account by clicking the link in your web settings "
            "or use `/start YOUR_API_KEY`.\n\n"
            "Once linked, you can:\n"
            "🎙️ Send voice messages\n"
            "🧠 Ask questions about your notes\n"
            "🛠️ Manage your integrations",
            parse_mode="Markdown"
        )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 **VoiceBrain Bot Help**\n\n"
        "Commands:\n"
        "/start - Start & link account\n"
        "/ask <query> - Ask AI about your notes\n"
        "/stats - View your usage stats\n"
        "/settings - Bot settings\n\n"
        "Just send a voice message to record a new note!",
        parse_mode="Markdown"
    )

@router.message(Command("ask"))
async def cmd_ask(message: types.Message, command: CommandObject):
    api_key = get_api_key(message.chat.id)
    if not api_key:
        await message.answer("⚠️ Please link your account first using `/start <api_key>`")
        return

    if not command.args:
        await message.answer("Please provide a question, e.g., `/ask What did I say about the meeting?`")
        return

    query = command.args
    await message.bot.send_chat_action(message.chat.id, "typing")
    # await message.answer("🧠 Searching your brain...") # Optional, maybe typing is enough

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/notes/ask",
                json={"question": query},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer found.")
                clarification = data.get("ask_clarification")
                note_id = data.get("note_id")

                text = f"🤖 **AI Answer:**\n\n{answer}"
                
                # If there's a clarification, add it with a special marker
                if clarification:
                    text += f"\n\n❓ **Clarification Needed:**\n_{clarification}_"
                    
                builder = InlineKeyboardBuilder()
                if note_id:
                    # In a real app we might link to the web dashboard
                    builder.button(text="👁️ View on Web", url=f"http://localhost:5173/dashboard?id={note_id}")
                
                await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
            else:
                await message.answer(f"❌ Error: {response.text}")
        except Exception as e:
            logger.error(f"Ask AI Error: {e}")
            await message.answer("❌ Failed to connect to VoiceBrain API.")

@router.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text(message: types.Message):
    """Handle text that isn't a command - could be a conversation or note update."""
    # For now, treat it as a general 'Ask AI' if linked
    api_key = get_api_key(message.chat.id)
    if not api_key:
        return # Transparent if not linked

    # Simple logic: if it's not a command, treat it as a question
    # This might be annoying, so maybe we only respond if they are in 'Ask Mode'
    # But as per requirements "The same functionality as the web app (chat...)"
    await cmd_ask(message, CommandObject(command="ask", args=message.text))
