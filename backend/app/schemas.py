from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime
import re
from pydantic import field_validator

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    full_name: Optional[str] = None
    is_pro: bool = False # Deprecated, use tier
    tier: str = "free"
    seconds_used_this_month: int = 0
    billing_cycle_start: Optional[datetime] = None
    language: str = "en"
    api_key: Optional[str] = None
    has_onboarded: bool = False
    role: Optional[str] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    has_onboarded: Optional[bool] = None
    role: Optional[str] = None
    language: Optional[str] = None

class NoteBase(BaseModel):
    title: Optional[str] = None
    transcription_text: Optional[str] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    transcription_text: Optional[str] = None
    tags: Optional[List[str]] = None
    mood: Optional[str] = None

class NoteEditRequest(BaseModel):
    title: str
    summary: str
    action_items: List[str]

class IntegrationStatus(BaseModel):
    provider: str
    status: str # SUCCESS, FAILED, PENDING
    timestamp: datetime
    error: Optional[str] = None

class NoteResponse(NoteBase):
    id: str
    audio_url: str
    summary: Optional[str] = None
    action_items: List[str] = []
    tags: List[str] = []
    mood: Optional[str] = None
    google_maps_url: Optional[str] = None
    yandex_maps_url: Optional[str] = None
    email_draft_id: Optional[str] = None
    status: str = "COMPLETED"
    processing_step: Optional[str] = None
    created_at: datetime
    ai_analysis: Optional[dict] = {}
    integration_status: List[IntegrationStatus] = []
    
    class Config:
        from_attributes = True

class IntegrationBase(BaseModel):
    provider: str
    credentials: dict

class IntegrationCreate(IntegrationBase):
    pass

class IntegrationResponse(BaseModel):
    id: str
    provider: str
    created_at: datetime
    is_active: bool = True
    masked_settings: Optional[dict] = {}
    status: Optional[str] = "active"
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str

class TagUsage(BaseModel):
    name: str
    count: int

class TagMergeRequest(BaseModel):
    source: str
    target: str

class RelatedNote(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    created_at: datetime
    similarity: float
