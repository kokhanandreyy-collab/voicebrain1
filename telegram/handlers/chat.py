import httpx
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.bot import get_api_key, set_api_key, API_BASE_URL, logger
from telegram.utils.formatting import escape_md, format_note_rich

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if command.args:
        api_key = command.args
        set_api_key(message.chat.id, api_key)
        await message.answer(
            f"✅ *Account linked\!*\n\n"
            "You can now send voice notes to record them or just talk to me using 'Ask AI' mode\.",
            parse_mode="MarkdownV2"
        )
    else:
        await message.answer(
            "👋 *Welcome to VoiceBrain\!*\n\n"
            "To get started, please link your account by clicking the link in your web settings "
            "or use `/start YOUR_API_KEY`\.\n\n"
            "Once linked, you can:\n"
            "🎙️ Send voice messages\n"
            "🧠 Ask questions about your notes\n"
            "🛠️ Manage your integrations",
            parse_mode="MarkdownV2"
        )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *VoiceBrain Bot Help*\n\n"
        "Commands:\n"
        "/start \- Start & link account\n"
        "/ask \<query\> \- Ask AI about your notes\n"
        "/notes \- List recent notes\n"
        "/integrations \- Manage integrations\n"
        "/settings \- Bot settings\n\n"
        "Just send a voice message to record a new note\!",
        parse_mode="MarkdownV2"
    )

@router.message(Command("ask"))
async def cmd_ask(message: types.Message, command: CommandObject):
    from telegram.bot import get_client
    from telegram.utils.formatting import escape_md
    
    client = get_client(message.chat.id)
    if not client.api_key:
        await message.answer("⚠️ Please link your account first using `/start <api_key>`")
        return

    if not command.args:
        await message.answer("Please provide a question, e.g., `/ask What did I say about the meeting?`")
        return

    query = command.args
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Send initial message
    status_msg = await message.answer("🤖 *AI Answer:* \n\n_", parse_mode="MarkdownV2")
    full_answer = ""
    chunk_count = 0

    try:
        async for chunk in client.ask_ai_stream(query):
            full_answer += chunk
            chunk_count += 1
            
            # Update message every 10 chunks to avoid rate limiting
            if chunk_count % 10 == 0:
                # Keep typing action active
                await message.bot.send_chat_action(message.chat.id, "typing")
                try:
                    await status_msg.edit_text(
                        f"🤖 *AI Answer:*\n\n{escape_md(full_answer)}\|",
                        parse_mode="MarkdownV2"
                    )
                except Exception:
                    pass 

        # Final edit
        await status_msg.edit_text(
            f"🤖 *AI Answer:*\n\n{escape_md(full_answer)}",
            parse_mode="MarkdownV2"
        )
        
        # Note: In a real scenario, we might want to check for clarifications too.
        # Since streaming endpoint currently only yields text, we might need 
        # a final JSON chunk or a separate call to find clarifications if needed.
        # For parity, we'll keep it simple for now or fetch clarifications separately.
        
    except Exception as e:
        logger.error(f"Ask AI Streaming Error: {e}")
        await status_msg.edit_text("❌ Failed to get a response from VoiceBrain.")
    finally:
        await client.close()

@router.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text(message: types.Message, state: FSMContext):
    """Handle text that isn't a command - could be a conversation or note update."""
    current_state = await state.get_state()
    if current_state is not None:
        return # Let the specific state handler deal with it

    api_key = get_api_key(message.chat.id)
    if not api_key:
        return # Transparent if not linked

    # Simple logic: if it's not a command, treat it as a question
    # This might be annoying, so maybe we only respond if they are in 'Ask Mode'
    # But as per requirements "The same functionality as the web app (chat...)"
    await cmd_ask(message, CommandObject(command="ask", args=message.text))
