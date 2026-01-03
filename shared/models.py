from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

# --- Logic/Refactoring Note ---
# These models are mirrors of the backend schemas. 
# In a full-stack context, these could be auto-generated for the frontend 
# using tools like openapi-typescript or pydantic-to-typescript.

class NoteBase(BaseModel):
    title: Optional[str] = None
    transcription_text: Optional[str] = None

class NoteResponse(NoteBase):
    id: str
    audio_url: str
    summary: Optional[str] = None
    action_items: List[str] = []
    tags: List[str] = []
    status: str = "COMPLETED"
    processing_step: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class IntegrationResponse(BaseModel):
    id: str
    provider: str
    created_at: datetime
    is_active: bool = True
    status: Optional[str] = "active"
    
    class Config:
        from_attributes = True

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    ask_clarification: Optional[str] = None
    note_id: Optional[str] = None

class ReplyRequest(BaseModel):
    answer: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    tier: str = "free"
    api_key: Optional[str] = None
