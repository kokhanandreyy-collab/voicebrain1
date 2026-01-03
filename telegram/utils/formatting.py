import re

def escape_md(text: str) -> str:
    """
    Escapes characters for Telegram MarkdownV2.
    """
    if not text:
        return ""
    # Characters that must be escaped with a preceding \
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def format_note_rich(note: dict) -> str:
    """
    Returns a richly formatted string for a note, matching web aesthetics.
    """
    title = note.get("title") or "Untitled Note"
    summary = note.get("summary", "No summary available.")
    action_items = note.get("action_items", [])
    tags = note.get("tags", [])
    
    # Using MarkdownV2
    text = f"📑 *{escape_md(title)}*\n\n"
    
    if summary:
        text += f"📝 *Summary:*\n{escape_md(summary)}\n\n"
    
    if action_items:
        text += "✅ *Action Items:*\n"
        for item in action_items:
            text += f"• {escape_md(str(item))}\n"
        text += "\n"
        
    if tags:
        text += "🏷️ " + " ".join([f"#{escape_md(t)}" for t in tags])
        
    return text
