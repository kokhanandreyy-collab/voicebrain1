import httpx
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.bot import get_api_key, API_BASE_URL, logger

router = Router()

@router.message(Command("integrations"))
async def cmd_integrations(message: types.Message):
    from telegram.bot import get_client
    from telegram.utils.formatting import escape_md
    
    client = get_client(message.chat.id)
    if not client.api_key:
        await message.answer("⚠️ Please link your account first.")
        return

    try:
        # Get user's active integrations
        integrations = await client.get_integrations()
        
        text = "🔌 *Your Integrations:*\n\n"
        if not integrations:
            text += "No integrations connected yet\. Go to settings on web to link Notion, Slack, etc\."
        else:
            for item in integrations:
                provider = item.get("provider")
                status = item.get("status", "active")
                text += f"• *{escape_md(provider.capitalize())}*: {escape_md(status.upper())}\n"
        
        text += "\n_Tap a button below to trigger manual sync for most recent notes\._"
        
        builder = InlineKeyboardBuilder()
        # Common ones for quick sync
        for provider in ['notion', 'todoist', 'slack', 'google_calendar', 'obsidian']:
            # Only add buttons for connected ones
            if any(i.get("provider") == provider for i in integrations):
                builder.button(text=f"🔄 Sync {provider.capitalize()}", callback_data=f"sync_all:{provider}")
        
        builder.adjust(2)
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Integrations Error: {e}")
        await message.answer("❌ Connection failed.")
    finally:
        await client.close()

@router.callback_query(F.data.startswith("sync_all:"))
async def sync_all_callback(callback: types.CallbackQuery):
    from telegram.bot import get_client
    provider = callback.data.split(":")[1]
    
    await callback.message.answer(f"⏳ Synchronizing your latest notes to {provider.capitalize()}...")
    
    client = get_client(callback.message.chat.id)
    try:
        # 1. Fetch latest notes
        notes = await client.get_notes(limit=5)
        success_count = 0
        for note in notes:
            try:
                await client.sync_note(note['id'], provider)
                success_count += 1
            except:
                continue
        
        await callback.message.answer(f"✅ Sync complete! {success_count} notes sent to {provider.capitalize()}.")
    except Exception as e:
        logger.error(f"Manual Sync Error: {e}")
        await callback.message.answer(f"❌ Sync failed for {provider}.")
    finally:
        await client.close()
    
    await callback.answer()

@router.callback_query(F.data.startswith("sync_note_menu:"))
async def sync_note_menu_callback(callback: types.CallbackQuery):
    from telegram.bot import get_client
    note_id = callback.data.split(":")[1]

    client = get_client(callback.message.chat.id)
    try:
        # Get active integrations to show relevant buttons
        ints = await client.get_integrations()
        builder = InlineKeyboardBuilder()
        for i in ints:
            p = i.get("provider")
            builder.button(text=f"Sync to {p.capitalize()}", callback_data=f"sync_note_exec:{note_id}:{p}")
        
        builder.button(text="🔙 Back", callback_data=f"view_note:{note_id}")
        builder.adjust(1)
        
        await callback.message.edit_text("Select integration to sync this note:", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Sync Menu Error: {e}")
        await callback.answer("Error.")
    finally:
        await client.close()

@router.callback_query(F.data.startswith("sync_note_exec:"))
async def sync_note_exec_callback(callback: types.CallbackQuery):
    from telegram.bot import get_client
    parts = callback.data.split(":")
    note_id = parts[2]
    provider = parts[3]
    
    await callback.answer(f"Syncing to {provider}...")
    client = get_client(callback.message.chat.id)
    try:
        await client.sync_note(note_id, provider)
        await callback.message.answer(f"✅ Note successfully synced to {provider.capitalize()}!")
    except Exception as e:
        logger.error(f"Sync Exec Error: {e}")
        await callback.message.answer("❌ Connection error during sync.")
    finally:
        await client.close()
