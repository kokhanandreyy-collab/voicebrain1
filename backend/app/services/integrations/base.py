from abc import ABC, abstractmethod
from app.models import Integration, Note
import logging

class BaseIntegration(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def sync(self, integration: Integration, note: Note):
        """
        Sync the note to the external service.
        :param integration: The user's integration record (settings, tokens)
        :param note: The processed note object
        """
    async def ensure_token_valid(self, integration: Integration):
        """
        Check if token is expired and refresh if necessary.
        Override this for OAuth2 providers.
        """
        pass

    def sanitize_text(self, text: str) -> str:
        """Remove control characters that might break JSON."""
        if not text:
            return ""
        # Keep printable chars + common whitespace
        return "".join(c for c in text if ord(c) >= 32 or c in "\n\r\t")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename allowing Unicode but removing system invalid chars."""
        if not filename:
            return "untitled"
        import re
        # Remove system-reserved characters: / \ : * ? " < > |
        # Also remove control characters
        s = re.sub(r'[\\/*?:"<>|]', "", filename)
        # Remove control characters
        s = "".join(c for c in s if ord(c) >= 32)
        return s.strip(" .")
