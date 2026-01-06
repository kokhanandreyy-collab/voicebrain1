from typing import Optional, Any, Dict

class VoiceBrainError(Exception):
    """Base exception class for VoiceBrain application."""
    def __init__(self, message: str, code: str = "internal_error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ServiceError(VoiceBrainError):
    """Raised when a third-party service fails (e.g. AI, Storage)."""
    def __init__(self, message: str, service_name: str, **kwargs):
        super().__init__(message, code=f"{service_name}_error", details=kwargs)

class IntegrationError(VoiceBrainError):
    """Raised when an external integration fails (e.g. Notion, Slack)."""
    pass

class ResourceNotFoundError(VoiceBrainError):
    """Raised when a requested resource (Note, User) is not found."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}", code="not_found", details={"id": resource_id})
