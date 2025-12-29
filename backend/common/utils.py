def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown V1."""
    if not text:
        return ""
    # Characters to escape in Markdown V1: _ * [ `
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f'\\{char}')
    return text
