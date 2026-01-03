import httpx
import re
from aiogram import Router, types, F
from telegram.bot import get_api_key, API_BASE_URL, logger

router = Router()

@router.message(F.reply_to_message & F.text)
async def handle_reply(message: types.Message):
    """
    Handle replies to bot messages, specifically clarifications.
    """
    api_key = get_api_key(message.chat.id)
    if not api_key:
        return

    original_msg = message.reply_to_message.text or ""
    
    # Check if the original message looks like a clarification request
    # Backend sends: "❓ Question: ... \n_Reply to answer_"
    if "Clarification Needed" in original_msg or "Question:" in original_msg:
        await message.answer("📝 Updating your memory...")
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Try to find the note ID. Since we can't change the backend to include it in the text,
                # we'll fetch the user's latest notes and find the one that has this question.
                notes_resp = await client.get(
                    f"{API_BASE_URL}/notes",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                note_id = None
                if notes_resp.status_code == 200:
                    notes = notes_resp.json()
                    # Look for the question text in the note's action items
                    # We'll try to extract the question from the original message
                    q_match = re.search(r"Question:\s*(.*)", original_msg)
                    question_text = q_match.group(1).strip() if q_match else ""
                    
                    for note in notes[:5]: # Check only recent 5 notes
                        action_items = note.get("action_items", [])
                        for item in action_items:
                            if question_text in str(item) or "Clarification Needed:" in str(item):
                                note_id = note.get("id")
                                break
                        if note_id: break

                # 2. Submit reply
                if note_id:
                    reply_resp = await client.post(
                        f"{API_BASE_URL}/notes/{note_id}/reply",
                        json={"answer": message.text},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0
                    )
                    if reply_resp.status_code == 200:
                        await message.answer("✨ Thank you! My adaptive memory has been updated.")
                    else:
                        await message.answer(f"❌ Failed to update memory: {reply_resp.text}")
                else:
                    # Fallback: Just upload as a new text note if we can't find the origin
                    # This ensures the information is at least recorded in RAG
                    await client.post(
                        f"{API_BASE_URL}/notes/upload",
                        json={"transcription_text": f"Reply to: {original_msg}\nAnswer: {message.text}"},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0
                    )
                    await message.answer("✅ Note updated (recorded as new context).")

            except Exception as e:
                logger.error(f"Clarification Reply Error: {e}")
                await message.answer("❌ Connection error.")
    else:
        # Just a normal reply, maybe continue the chat?
        from telegram.handlers.chat import cmd_ask
        from aiogram.filters import CommandObject
        await cmd_ask(message, CommandObject(command="ask", args=message.text))

@router.callback_query(F.data.startswith("clarify_"))
async def handle_clarify_callback(callback: types.CallbackQuery):
    """
    If we ever use inline buttons for clarifications (future-proofing).
    """
    note_id = callback.data.replace("clarify_", "")
    await callback.message.answer(f"Please reply to this message with your answer for note {note_id}:")
    await callback.answer()
