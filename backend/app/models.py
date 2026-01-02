from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, JSON, LargeBinary, DateTime, ForeignKey, Table, Text, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# Many-to-Many for Note Tags
note_tags = Table(
    'note_tags',
    Base.metadata,
    Column('note_id', String, ForeignKey('notes.id')),
    Column('tag_id', String, ForeignKey('tags.id'))
)

class UserTier:
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

TIER_LIMITS = {
    "free": {
        "monthly_transcription_seconds": 1800, # 30 mins
        "integrations": 1,
        "max_duration_seconds": 300, # 5 mins per upload
    },
    "pro": {
        "monthly_transcription_seconds": 3600 * 3, # 3 hours
        "integrations": 50,
        "max_duration_seconds": 3600, # 1 hour per upload
    },
    "premium": {
        "monthly_transcription_seconds": float('inf'),
        "integrations": 50,
        "max_duration_seconds": 3600 * 2, # 2 hours per upload
    }
}

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True) # User context for AI
    target_language = Column(String, default='Original')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Subscription/Tier
    tier = Column(String, default=UserTier.FREE)
    is_pro = Column(Boolean, default=False) # Legacy toggler, prefer 'tier' check
    billing_cycle_start = Column(DateTime(timezone=True), nullable=True)
    billing_period = Column(String, default="monthly") # monthly, yearly
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Usage
    monthly_usage_seconds = Column(Integer, default=0)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    # Gamification
    streak_days = Column(Integer, default=0)
    last_note_date = Column(DateTime(timezone=True), nullable=True)

    # Telegram Integration
    telegram_chat_id = Column(String, nullable=True)
    
    # Web Push
    push_subscriptions = Column(JSON, default=[]) # List of subscriptions

    # Feature Flags
    feature_flags = Column(JSON, default={"all_integrations": True})

    # Admin Role
    role = Column(String, default='user') # 'user' or 'admin' 

    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="user")

class NoteRelation(Base):
    __tablename__ = "note_relations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_note_id = Column(String, ForeignKey("notes.id"), nullable=False)
    target_note_id = Column(String, ForeignKey("notes.id"), nullable=False)
    relation_type = Column(String, nullable=False) # caused, related, contradicts
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NoteStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ANALYZED = "ANALYZED"
    SYNCED = "SYNCED" # Intermediate state if needed, or COMPLETED
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    
    title = Column(String, nullable=True)
    transcription_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    audio_url = Column(String, nullable=True) # Legacy URL
    storage_key = Column(String, nullable=True) # S3 Key
    duration_seconds = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_favorite = Column(Boolean, default=False)
    
    # New Metadata
    action_items = Column(JSON, default=[])
    calendar_events = Column(JSON, default=[])
    tags = Column(JSON, default=[]) # Stored as JSON array for simplicity
    diarization = Column(JSON, default=[]) # [{speaker: "A", text: "..."}]
    
    # Health extraction
    health_data = Column(JSON, nullable=True) # {steps: 1000, calories: 500}
    
    # Status
    # Status
    status = Column(String, default=NoteStatus.PENDING) # PENDING, PROCESSING, ANALYZED, COMPLETED, FAILED
    processing_step = Column(String, nullable=True) # For UI progress (e.g. "Transcribing...")
    processing_error = Column(Text, nullable=True)
    
    # UI Metadata
    mood = Column(String, nullable=True)
    google_maps_url = Column(String, nullable=True)
    yandex_maps_url = Column(String, nullable=True)
    reminder_id = Column(String, nullable=True)
    email_draft_id = Column(String, nullable=True)
    readwise_highlight_id = Column(String, nullable=True)
    obsidian_note_path = Column(String, nullable=True)
    yandex_task_id = Column(String, nullable=True)
    twogis_url = Column(String, nullable=True)
    mapsme_url = Column(String, nullable=True)

    # Agentic Workflow Metadata (Hidden fields for pipeline)
    ai_analysis = Column(JSON, nullable=True) # Full raw analysis
    cluster_id = Column(String, nullable=True) # For topic clustering

    user = relationship("User", back_populates="notes")
    logs = relationship("IntegrationLog", back_populates="note")
    embedding_data = relationship("NoteEmbedding", uselist=False, back_populates="note")

class NoteEmbedding(Base):
    __tablename__ = "note_embeddings"
    
    note_id = Column(String, ForeignKey("notes.id"), primary_key=True)
    from pgvector.sqlalchemy import VECTOR
    embedding = Column(VECTOR(1536)) 
    
    note = relationship("Note", back_populates="embedding_data")

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    provider = Column(String, nullable=False) # notion, todoist, google_calendar
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    encrypted_access_token = Column(LargeBinary, nullable=True)
    encrypted_refresh_token = Column(LargeBinary, nullable=True)
    google_maps_access_token = Column(LargeBinary, nullable=True)
    yandex_maps_access_token = Column(LargeBinary, nullable=True)
    apple_reminders_token = Column(LargeBinary, nullable=True)
    google_tasks_token = Column(LargeBinary, nullable=True)
    gmail_token = Column(LargeBinary, nullable=True)
    outlook_token = Column(LargeBinary, nullable=True)
    readwise_token = Column(LargeBinary, nullable=True)
    obsidian_vault_path = Column(LargeBinary, nullable=True)
    yandex_tasks_token = Column(LargeBinary, nullable=True)
    twogis_token = Column(LargeBinary, nullable=True)
    mapsme_path = Column(LargeBinary, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSON, default={}) # e.g. default_database_id
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="integrations")

    @property
    def auth_token(self) -> str:
        """Returns decrypted access token. Fallback to plaintext for migration."""
        from app.core.security import decrypt_token
        if self.encrypted_access_token:
            return decrypt_token(self.encrypted_access_token)
        return self.access_token

    @property
    def auth_refresh_token(self) -> Optional[str]:
        """Returns decrypted refresh token. Fallback to plaintext for migration."""
        from app.core.security import decrypt_token
        if self.encrypted_refresh_token:
            return decrypt_token(self.encrypted_refresh_token)
        return self.refresh_token

class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String, ForeignKey("integrations.id")) # Link to integration definition
    note_id = Column(String, ForeignKey("notes.id"))
    status = Column(String) # SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    note = relationship("Note", back_populates="logs")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True)

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True) # "pro", "premium" (manually set for simplicity)
    name = Column(String, unique=True, nullable=False) # Pro, Premium
    
    # Pricing
    price_monthly_usd = Column(Float, default=0.0)
    price_yearly_usd = Column(Float, default=0.0)
    price_monthly_rub = Column(Float, default=0.0)
    price_yearly_rub = Column(Float, default=0.0)
    
    # Metadata
    features = Column(JSON, default={}) # storage, minutes, integrations
    is_active = Column(Boolean, default=True)

class AdminLog(Base):
    __tablename__ = "admin_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String, ForeignKey("users.id"))
    action = Column(String, nullable=False) # e.g., "UPDATE_PLAN"
    target_id = Column(String, nullable=True) # e.g., plan_id
    details = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, nullable=False, index=True)
    discount_percent = Column(Integer, nullable=False) # e.g. 20 for 20%
    usage_limit = Column(Integer, default=100)
    times_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    key = Column(String, primary_key=True) # e.g. "general_analysis"
    text = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
class LongTermMemory(Base):
    __tablename__ = "long_term_memories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    
    summary_text = Column(Text, nullable=False)
    importance_score = Column(Float, default=8.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    from pgvector.sqlalchemy import VECTOR
    embedding = Column(VECTOR(1536))

    user = relationship("User")
