import httpx
import re
from aiogram import Router, types, F
from telegram.bot import get_api_key, API_BASE_URL, logger

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

class ClarifyStates(StatesGroup):
    waiting_for_answer = State()
    confirming = State()

@router.message(F.reply_to_message & F.text)
async def start_clarification_from_reply(message: types.Message, state: FSMContext):
    """
    Triggered when user replies to a bot message containing a question.
    """
    original_msg = message.reply_to_message.text or ""
    if "Clarification Needed" in original_msg or "Question:" in original_msg:
        # Extract question
        q_match = re.search(r"Question:\s*(.*)", original_msg)
        question_text = q_match.group(1).strip() if q_match else original_msg[:50]
        
        await state.update_data(question=question_text, answer=message.text, original_msg_id=message.reply_to_message.message_id)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Confirm & Update Memory", callback_data="confirm_clarify")
        builder.button(text="✏️ Edit Answer", callback_data="edit_clarify")
        builder.adjust(1)
        
        await message.answer(
            f"🤔 *Confirm your answer:*\n\n"
            f"❓ *Question:* {question_text}\n"
            f"💡 *Your Answer:* {message.text}\n\n"
            "By confirming, you'll help me better understand your preferences.",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(ClarifyStates.confirming)

@router.callback_query(F.data == "edit_clarify", ClarifyStates.confirming)
async def edit_clarify_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Please send your revised answer:")
    await state.set_state(ClarifyStates.waiting_for_answer)
    await callback.answer()

@router.message(ClarifyStates.waiting_for_answer)
async def process_revised_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    question_text = data.get("question")
    
    await state.update_data(answer=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm & Update Memory", callback_data="confirm_clarify")
    builder.button(text="✏️ Edit Again", callback_data="edit_clarify")
    builder.adjust(1)
    
    await message.answer(
        f"🤔 *Confirm your revised answer:*\n\n"
        f"❓ *Question:* {question_text}\n"
        f"💡 *Your Answer:* {message.text}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(ClarifyStates.confirming)

@router.callback_query(F.data == "confirm_clarify", ClarifyStates.confirming)
async def confirm_clarify_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    answer = data.get("answer")
    api_key = get_api_key(callback.message.chat.id)
    
    await callback.message.edit_text("⏳ Updating adaptive memory...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Note resolution logic same as before or improved
            # (Fetching notes to find the ID)
            notes_resp = await client.get(
                f"{API_BASE_URL}/notes",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"limit": 5}
            )
            
            note_id = None
            if notes_resp.status_code == 200:
                notes = notes_resp.json()
                question_text = data.get("question")
                for note in notes:
                    if any(question_text in str(item) for item in note.get("action_items", [])):
                        note_id = note.get("id")
                        break
            
            if note_id:
                resp = await client.post(
                    f"{API_BASE_URL}/notes/{note_id}/reply",
                    json={"answer": answer},
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    await callback.message.edit_text("✅ *Adaptive Memory Updated!* ✨\nThank you for helping me learn your preferences.")
                else:
                    await callback.message.edit_text(f"❌ Failed to update: {resp.text}")
            else:
                # Fallback to new note
                await client.post(
                    f"{API_BASE_URL}/notes/upload",
                    json={"transcription_text": f"Answer: {answer}\nContext: {data.get('question')}"},
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                await callback.message.edit_text("✅ *Recorded!* My memory has been updated (as new context).")
                
        except Exception as e:
            logger.error(f"Clarification confirm error: {e}")
            await callback.message.edit_text("❌ Connection error.")
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("clarify_"))
async def handle_clarify_callback(callback: types.CallbackQuery):
    """
    If we ever use inline buttons for clarifications (future-proofing).
    """
    note_id = callback.data.replace("clarify_", "")
    await callback.message.answer(f"Please reply to this message with your answer for note {note_id}:")
    await callback.answer()
