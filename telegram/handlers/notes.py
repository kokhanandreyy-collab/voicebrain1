import httpx
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telegram.bot import get_api_key, API_BASE_URL, logger

router = Router()

class NoteStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_title = State()

@router.message(Command("notes"))
async def cmd_list_notes(message: types.Message):
    await list_notes_paged(message, page=0)

async def list_notes_paged(message: types.Message, page: int = 0, edit: bool = False):
    from telegram.bot import get_client
    from telegram.utils.formatting import escape_md
    
    limit = 5
    skip = page * limit
    client = get_client(message.chat.id if hasattr(message, "chat") else message.from_user.id)
    
    if not client.api_key:
        await (message.edit_text if edit else message.answer)("⚠️ Please link your account first.")
        return

    try:
        notes = await client.get_notes(limit=limit, skip=skip)
        if not notes and page == 0:
            await (message.edit_text if edit else message.answer)("📝 You don't have any notes yet.")
            return

        builder = InlineKeyboardBuilder()
        text = f"📂 *Your Notes \(Page {page + 1}\):*\n\n"
        
        for note in notes:
            title = note.get("title") or "Untitled"
            note_id = note.get("id")
            created_at = note.get("created_at", "").split("T")[0]
            text += f"• *{escape_md(title)}* \({escape_md(created_at)}\)\n"
            builder.button(text=f"👁️ {title[:25]}", callback_data=f"view_note:{note_id}:{page}")
        
        builder.adjust(1)
        
        # Pagination Buttons
        nav_btns = []
        if page > 0:
            nav_btns.append(types.InlineKeyboardButton(text="⬅️ Prev", callback_data=f"list_page:{page - 1}"))
        if len(notes) == limit:
            nav_btns.append(types.InlineKeyboardButton(text="Next ➡️", callback_data=f"list_page:{page + 1}"))
        
        if nav_btns:
            builder.row(*nav_btns)

        if edit:
            await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="MarkdownV2")
        else:
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode="MarkdownV2")
            
    except Exception as e:
        logger.error(f"List Notes Error: {e}")
        await (message.edit_text if edit else message.answer)("❌ Connection failed.")
    finally:
        await client.close()

@router.callback_query(F.data.startswith("list_page:"))
async def list_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    await list_notes_paged(callback.message, page=page, edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("view_note:"))
async def view_note_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    note_id = parts[1]
    page = parts[2] if len(parts) > 2 else "0"
    
    from telegram.bot import get_client
    from telegram.utils.formatting import escape_md, format_note_rich, format_clarification_block
    
    client = get_client(callback.message.chat.id)
    try:
        note = await client.get_note_detail(note_id)
        text = format_note_rich(note)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🗑️ Delete", callback_data=f"delete_note:{note_id}:{page}")
        builder.button(text="🔄 Sync", callback_data=f"sync_note_menu:{note_id}")
        builder.button(text="🔙 Back", callback_data=f"list_page:{page}")
        builder.adjust(2)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="MarkdownV2")

        # Scan for clarifications in action items
        action_items = note.get("action_items") or []
        for item in action_items:
            if "Clarification Needed:" in str(item):
                question = str(item).replace("Clarification Needed:", "").strip()
                clarify_text = format_clarification_block(question)
                
                clarify_builder = InlineKeyboardBuilder()
                clarify_builder.button(text="Answer 📝", callback_data=f"answer_clarify:{note_id}")
                
                await callback.message.answer(
                    clarify_text, 
                    reply_markup=clarify_builder.as_markup(), 
                    parse_mode="MarkdownV2"
                )
    except Exception as e:
        logger.error(f"View Note Error: {e}")
        await callback.answer("❌ Note details unavailable.", show_alert=True)
    finally:
        await client.close()

@router.callback_query(F.data == "list_notes")
async def list_notes_back(callback: types.CallbackQuery):
    await cmd_list_notes(callback.message)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_note:"))
async def delete_note_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    note_id = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    
    from telegram.bot import get_client
    client = get_client(callback.message.chat.id)
    try:
        await client.delete_note(note_id)
        await callback.answer("✅ Note deleted!", show_alert=True)
        await list_notes_paged(callback.message, page=page, edit=True)
    except Exception as e:
        logger.error(f"Delete Note Error: {e}")
        await callback.answer("❌ Connection error.")
    finally:
        await client.close()

@router.message(Command("new_note"))
async def cmd_new_note(message: types.Message, state: FSMContext):
    api_key = get_api_key(message.chat.id)
    if not api_key:
        await message.answer("⚠️ Please link your account first.")
        return
    
    await message.answer("📝 Please send the text for your new note:")
    await state.set_state(NoteStates.waiting_for_text)

@router.message(NoteStates.waiting_for_text)
async def process_new_note_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("📎 Great! Now send a title for this note (or type /skip to use AI title):")
    await state.set_state(NoteStates.waiting_for_title)

@router.message(NoteStates.waiting_for_title)
async def process_new_note_title(message: types.Message, state: FSMContext):
    from telegram.bot import get_client
    data = await state.get_data()
    title = message.text if message.text != "/skip" else None
    api_key = get_api_key(message.chat.id)

    status_msg = await message.answer("🧠 Processing your text note...")
    
    client = get_client(message.chat.id)
    try:
        # Use the NEW shared client method
        await client.upload_text_note(text=data['text'], title=title)
        
        await status_msg.edit_text(
            "✅ *Note Saved\!*\n\n"
            "Your text note has been recorded and added to your brain\. "
            "It will be analyzed shortly\.",
            parse_mode="MarkdownV2"
        )
            
    except Exception as e:
        logger.error(f"New Note Error: {e}")
        await status_msg.edit_text("❌ Failed to save text note\. Please try again later\.")
    finally:
        await client.close()
    
    await state.clear()
