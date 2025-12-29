from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.models import User
from app.dependencies import get_current_user
from app.core.config import settings
from app.core.bot import bot

router = APIRouter()

class FeedbackData(BaseModel):
    message: str
    type: str # 'bug', 'feature'
    logs: Optional[str] = None
    url: Optional[str] = None

@router.post("/")
async def submit_feedback(
    data: FeedbackData,
    current_user: User = Depends(get_current_user)
):
    """
    Send feedback to Admin via Telegram.
    """
    if not settings.ADMIN_TELEGRAM_CHAT_ID:
        return {"status": "saved_locally", "message": "Feedback received (Admin notifications not configured)."}

    if not bot:
        return {"status": "error", "message": "Bot not initialized"}

    try:
        icon = "🐞" if data.type == "bug" else "💡"
        
        msg = (
            f"{icon} **{data.type.upper()} REPORT**\n\n"
            f"👤 **User:** {current_user.email} ({current_user.tier})\n"
            f"🔗 **URL:** {data.url or 'N/A'}\n"
            f"📝 **Message:**\n{data.message}\n"
        )
        
        await bot.send_message(
            chat_id=settings.ADMIN_TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode="Markdown"
        )
        
        if data.logs and len(data.logs) > 0:
             # If logs are long, maybe send as file? 
             # For simplicity, send as second message or block if short.
             if len(data.logs) < 3000:
                await bot.send_message(
                    chat_id=settings.ADMIN_TELEGRAM_CHAT_ID,
                    text=f"📜 **Logs:**\n```\n{data.logs}\n```",
                    parse_mode="Markdown"
                )
             else:
                 # Too long, truncate
                 truncated = data.logs[:3000] + "\n...[TRUNCATED]"
                 await bot.send_message(
                    chat_id=settings.ADMIN_TELEGRAM_CHAT_ID,
                    text=f"📜 **Logs (Truncated):**\n```\n{truncated}\n```",
                    parse_mode="Markdown"
                )

        return {"status": "sent"}
    except Exception as e:
        print(f"Feedback Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send feedback")
