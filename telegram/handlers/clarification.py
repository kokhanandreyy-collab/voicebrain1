import httpx
import re
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.bot import get_api_key, API_BASE_URL, logger, bot
from telegram.utils.formatting import escape_md, format_clarification_block

router = Router()

class ClarifyStates(StatesGroup):
    waiting_for_answer = State()
    confirming = State()

@router.callback_query(F.data.startswith("answer_clarify:"))
async def answer_clarify_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Called when 'Answer 📝' button is pressed on a clarification block.
    """
    note_id = callback.data.split(":")[1]
    original_text = callback.message.text or ""
    
    # Extract question from the block
    # Block format: 🟠 Clarification Needed\n📜 <question>\n\n...
    lines = original_text.split("\n")
    question = lines[1][2:].strip() if len(lines) > 1 else "Unknown question"
    
    await state.update_data(
        question=question, 
        note_id=note_id if note_id != "none" else None,
        clarification_msg_id=callback.message.message_id,
        chat_id=callback.message.chat.id
    )
    
    await callback.message.answer(f"📝 *Answering:* _{escape_md(question)}_\n\nPlease send your answer below:", parse_mode="MarkdownV2")
    await state.set_state(ClarifyStates.waiting_for_answer)
    await callback.answer()

@router.message(F.reply_to_message & F.text)
async def start_clarification_from_reply(message: types.Message, state: FSMContext):
    """
    Triggered when user replies to a bot message containing a question.
    """
    original_msg = message.reply_to_message.text or ""
    if "Clarification Needed" in original_msg or "🟠" in original_msg:
        # Extract question
        lines = original_msg.split("\n")
        question = lines[1][2:].strip() if len(lines) > 1 else original_msg[:50]
        
        await state.update_data(
            question=question, 
            answer=message.text, 
            clarification_msg_id=message.reply_to_message.message_id,
            chat_id=message.chat.id
        )
        await show_confirmation(message, state)

@router.message(ClarifyStates.waiting_for_answer)
async def process_manual_answer(message: types.Message, state: FSMContext):
    await state.update_data(answer=message.text)
    await show_confirmation(message, state)

async def show_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    question = data.get("question")
    answer = message.text
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm & Save", callback_data="confirm_clarify")
    builder.button(text="✏️ Edit Answer", callback_data="edit_clarify")
    builder.adjust(1)
    
    await message.answer(
        f"🤔 *Confirm your answer:*\n\n"
        f"❓ *Q:* _{escape_md(question)}_\n"
        f"💡 *A:* {escape_md(answer)}",
        reply_markup=builder.as_markup(),
        parse_mode="MarkdownV2"
    )
    await state.set_state(ClarifyStates.confirming)

@router.callback_query(F.data == "edit_clarify", ClarifyStates.confirming)
async def edit_clarify_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Please send your revised answer:")
    await state.set_state(ClarifyStates.waiting_for_answer)
    await callback.answer()

@router.callback_query(F.data == "confirm_clarify", ClarifyStates.confirming)
async def confirm_clarify_callback(callback: types.CallbackQuery, state: FSMContext):
    from telegram.bot import get_client
    data = await state.get_data()
    answer = data.get("answer")
    note_id = data.get("note_id")
    question = data.get("question")
    clarification_msg_id = data.get("clarification_msg_id")
    chat_id = data.get("chat_id")
    
    client = get_client(callback.message.chat.id)
    confirm_msg = await callback.message.edit_text("⏳ Updating adaptive memory...")
    
    try:
        # If note_id missing, try to find it
        if not note_id:
            notes = await client.get_notes(limit=10)
            for note in notes:
                if any(question in str(item) for item in note.get("action_items", [])):
                    note_id = note.get("id")
                    break

        if note_id:
            await client.reply_to_clarification(note_id, answer)
            
            # 1. Update the original clarification message to 'Resolved'
            resolved_text = format_clarification_block(question, answer, resolved=True)
            
            # Add 'Edit Answer' button to the resolved block
            edit_builder = InlineKeyboardBuilder()
            edit_builder.button(text="🔄 Edit Answer", callback_data=f"answer_clarify:{note_id}")
            
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=clarification_msg_id,
                    text=resolved_text,
                    reply_markup=edit_builder.as_markup(),
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.warning(f"Could not edit original clarification msg: {e}")

            await confirm_msg.edit_text("✅ *Adaptive Memory Updated\!* ✨\nYour preferences have been applied\.")
        else:
            # Fallback to new note
            await client.upload_text_note(f"Answer: {answer}\nContext: {question}")
            await confirm_msg.edit_text("✅ *Recorded\!* My memory has been updated (as new context)\.")
            
    except Exception as e:
        logger.error(f"Clarification confirm error: {e}")
        await confirm_msg.edit_text("❌ Connection error\.")
    finally:
        await client.close()
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("clarify_"))
async def handle_old_clarify_callback(callback: types.CallbackQuery):
    note_id = callback.data.replace("clarify_", "")
    await callback.message.answer(f"Please reply to this message with your answer for note {note_id}:")
    await callback.answer()
