import os

# Telegram Bot Feature Toggles
# Matching web parity: some features might be experimental or pro-only
ENABLE_INTEGRATIONS = True
ENABLE_VOICE_COMMANDS = False # TODO: Implement voice command parsing
ENABLE_ADAPTIVE_MEMORY = True
MAX_RECENT_NOTES = 10

# UI Settings
EMOJI_CONFIRM = "✅"
EMOJI_WAIT = "⏳"
EMOJI_ERROR = "❌"
EMOJI_SPARKLES = "✨"

# Parity Check: Missing Web Features
# - [ ] Graph View / Visual Memory
# - [ ] Batch note editing
# - [ ] Advanced Tag filtering
# - [ ] Custom AI Prompt settings per note
