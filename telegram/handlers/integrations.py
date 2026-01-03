import httpx
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.bot import get_api_key, API_BASE_URL, logger

router = Router()

@router.message(Command("integrations"))
async def cmd_integrations(message: types.Message):
    api_key = get_api_key(message.chat.id)
    if not api_key:
        await message.answer("⚠️ Please link your account first.")
        return

    async with httpx.AsyncClient() as client:
        try:
            # Get user's active integrations
            response = await client.get(
                f"{API_BASE_URL}/integrations",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                integrations = response.json()
                from telegram.utils.formatting import escape_md
                
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
            else:
                await message.answer(f"❌ Error: {response.status_code}")
        except Exception as e:
            logger.error(f"Integrations Error: {e}")
            await message.answer("❌ Connection failed.")

@router.callback_query(F.data.startswith("sync_all:"))
async def sync_all_callback(callback: types.CallbackQuery):
    provider = callback.data.split(":")[1]
    api_key = get_api_key(callback.message.chat.id)
    
    await callback.message.answer(f"⏳ Synchronizing your latest notes to {provider.capitalize()}...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Fetch latest notes
            notes_resp = await client.get(
                f"{API_BASE_URL}/notes",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"limit": 5},
                timeout=10.0
            )
            
            if notes_resp.status_code == 200:
                notes = notes_resp.json()
                success_count = 0
                for note in notes:
                    sync_resp = await client.post(
                        f"{API_BASE_URL}/notes/{note['id']}/share/{provider}",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=15.0
                    )
                    if sync_resp.status_code == 200:
                        success_count += 1
                
                await callback.message.answer(f"✅ Sync complete! {success_count} notes sent to {provider.capitalize()}.")
            else:
                await callback.message.answer("❌ Failed to fetch notes for sync.")
        except Exception as e:
            logger.error(f"Manual Sync Error: {e}")
            await callback.message.answer(f"❌ Sync failed for {provider}.")
    
    await callback.answer()

@router.callback_query(F.data.startswith("sync_note_menu:"))
async def sync_note_menu_callback(callback: types.CallbackQuery):
    note_id = callback.data.split(":")[1]
    api_key = get_api_key(callback.message.chat.id)

    async with httpx.AsyncClient() as client:
        try:
            # Get active integrations to show relevant buttons
            resp = await client.get(
                f"{API_BASE_URL}/integrations",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if resp.status_code == 200:
                ints = resp.json()
                builder = InlineKeyboardBuilder()
                for i in ints:
                    p = i.get("provider")
                    builder.button(text=f"Sync to {p.capitalize()}", callback_data=f"sync_note_exec:{note_id}:{p}")
                
                builder.button(text="🔙 Back", callback_data=f"view_note:{note_id}")
                builder.adjust(1)
                
                await callback.message.edit_text("Select integration to sync this note:", reply_markup=builder.as_markup())
            else:
                await callback.answer("Error fetching integrations.")
        except Exception as e:
            logger.error(f"Sync Menu Error: {e}")
            await callback.answer("Error.")

@router.callback_query(F.data.startswith("sync_note_exec:"))
async def sync_note_exec_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    note_id = parts[2]
    provider = parts[3]
    api_key = get_api_key(callback.message.chat.id)
    
    await callback.answer(f"Syncing to {provider}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/notes/{note_id}/share/{provider}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20.0
            )
            if response.status_code == 200:
                await callback.message.answer(f"✅ Note successfully synced to {provider.capitalize()}!")
            else:
                await callback.message.answer(f"❌ Sync failed: {response.text}")
        except Exception as e:
            logger.error(f"Sync Exec Error: {e}")
            await callback.message.answer("❌ Connection error during sync.")
