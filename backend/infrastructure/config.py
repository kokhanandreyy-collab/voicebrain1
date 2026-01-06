from typing import Optional
from pydantic import field_validator, ValidationInfo
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VoiceBrain"
    # Env
    ENVIRONMENT: str = "development"
    SECRET_KEY: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None
    VITE_APP_URL: str = "http://localhost:5173"
    # Comma-separated list of origins. In prod, set to: "https://voicebrain.app,https://web.telegram.org"
    ALLOWED_ORIGINS: str = "http://localhost:5173" 
    
    # Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_GLOBAL: str = "100/minute"

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[str], info: ValidationInfo) -> str:
        if v:
            return v
            
        # Check environment from data
        env = info.data.get("ENVIRONMENT", "development")
        
        if env == "development":
             print("\033[93mWARNING: SECRET_KEY not found. Using dev key.\033[0m")
             return "dev_secret_key_insecure"
            
        raise ValueError("SECRET_KEY must be set in production environment!")

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: Optional[str], info: ValidationInfo) -> str:
        if v:
            return v
        
        env = info.data.get("ENVIRONMENT", "development")
        if env == "development":
            # For development, we return a valid but insecure key if not provided
            return "GiqaWijI1m94xqMrFtlzpMr2qOzYKyqHWjkowdri1-0="
            
        raise ValueError("ENCRYPTION_KEY must be set in production environment!")

    API_V1_STR: str = "/api"
    API_BASE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://voicebrain:voicebrain_secret@db:5432/voicebrain_db"
    POSTGRES_USER: str = "voicebrain"
    POSTGRES_PASSWORD: str = "voicebrain_secret"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "voicebrain_db"
    REDIS_URL: str = "redis://redis:6379"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # External Services
    OPENAI_API_KEY: Optional[str] = None
    ASSEMBLYAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # Google Maps
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALENDAR_CLIENT_ID: Optional[str] = None
    GOOGLE_CALENDAR_CLIENT_SECRET: Optional[str] = None
    
    # Yandex Maps
    YANDEX_MAPS_API_KEY: Optional[str] = None
    YANDEX_OAUTH_CLIENT_ID: Optional[str] = None
    YANDEX_OAUTH_CLIENT_SECRET: Optional[str] = None
    
    # Tasks
    APPLE_CLIENT_ID: Optional[str] = None
    APPLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_TASKS_CLIENT_ID: Optional[str] = None
    GOOGLE_TASKS_CLIENT_SECRET: Optional[str] = None
    
    # Email
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    
    # Readwise
    READWISE_API_KEY: Optional[str] = None
    
    # Yandex Tasks
    YANDEX_TASKS_CLIENT_ID: Optional[str] = None
    YANDEX_TASKS_CLIENT_SECRET: Optional[str] = None

    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "voicebrain-audio-dev"
    S3_ENDPOINT_URL: Optional[str] = None
    S3_REGION_NAME: str = "us-east-1"

    # Auth & Integrations
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    VK_CLIENT_ID: Optional[str] = None
    VK_CLIENT_SECRET: Optional[str] = None
    MAILRU_CLIENT_ID: Optional[str] = None
    MAILRU_CLIENT_SECRET: Optional[str] = None
    TWITTER_CLIENT_ID: Optional[str] = None
    TWITTER_CLIENT_SECRET: Optional[str] = None
    DROPBOX_CLIENT_ID: Optional[str] = None
    DROPBOX_CLIENT_SECRET: Optional[str] = None
    TODOIST_CLIENT_ID: Optional[str] = None
    TODOIST_CLIENT_SECRET: Optional[str] = None
    LINEAR_CLIENT_ID: Optional[str] = None
    LINEAR_CLIENT_SECRET: Optional[str] = None
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None
    CLICKUP_CLIENT_ID: Optional[str] = None
    CLICKUP_CLIENT_SECRET: Optional[str] = None
    NOTION_CLIENT_ID: Optional[str] = None
    NOTION_CLIENT_SECRET: Optional[str] = None
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    AMOCRM_CLIENT_ID: Optional[str] = None
    AMOCRM_CLIENT_SECRET: Optional[str] = None


    # SMTP Settings (for Email integration)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey" 
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

    # Observability
    SENTRY_DSN: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
