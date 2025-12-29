import os
import secrets
from typing import Optional, Any
from pydantic import field_validator, ValidationInfo
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VoiceBrain"
    # Env
    ENVIRONMENT: str = "development"
    SECRET_KEY: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[str], info: ValidationInfo) -> str:
        if v:
            return v
            
        # Check environment from data or os
        env = info.data.get("ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
        
        if env == "development":
             print("\033[93mWARNING: SECRET_KEY not found. Using dev key.\033[0m")
             return "dev_secret_key_insecure"
            
        raise ValueError("SECRET_KEY must be set in production environment!")

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: Optional[str], info: ValidationInfo) -> str:
        if v:
            return v
        
        env = info.data.get("ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
        if env == "development":
            # For development, we return a valid but insecure key if not provided
            # generated via Fernet.generate_key()
            return "GiqaWijI1m94xqMrFtlzpMr2qOzYKyqHWjkowdri1-0="
            
        raise ValueError("ENCRYPTION_KEY must be set in production environment!")

    API_V1_STR: str = "/api"
    API_BASE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://voicebrain:voicebrain_secret@db:5432/voicebrain_db"
    REDIS_URL: str = "redis://redis:6379"

    # External Services
    OPENAI_API_KEY: Optional[str] = None
    ASSEMBLYAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = "voicebrain-audio-dev"

    # Auth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # SMTP Settings (for Email integration)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey" # Default for SendGrid or similar, or real email
    SMTP_PASSWORD: str = "password"
    SMTP_FROM: str = "VoiceBrain <no-reply@voicebrain.app>"

    # Payment (Prodamus)
    PRODAMUS_KEY: str = "secret_key"
    PRODAMUS_URL: str = "https://demo.payform.ru"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    ADMIN_TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Web Push
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_CLAIMS_EMAIL: str = "mailto:admin@voicebrain.app"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
