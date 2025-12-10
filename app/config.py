from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Ensure the URL uses the asyncpg driver."""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        if self.DATABASE_URL.startswith("postgresql+psycopg2://"):
             return self.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        return self.DATABASE_URL

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Application
    APP_NAME: str = "Broiler Farm Management API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Notifications (for future implementation)
    SMS_PROVIDER_API_KEY: Optional[str] = None
    EMAIL_API_KEY: Optional[str] = None
    PUSH_NOTIFICATION_KEY: Optional[str] = None

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = "notifications@broiler-manager.com"
    EMAILS_FROM_NAME: Optional[str] = "Broiler Manager"

    # M-Pesa
    MPESA_CONSUMER_KEY: str = "place_holder"
    MPESA_CONSUMER_SECRET: str = "place_holder"
    MPESA_PASSKEY: str = "place_holder"
    MPESA_SHORTCODE: str = "174379" # Default test shortcode
    MPESA_CALLBACK_URL: str = "https://your-domain.com/api/v1/billing/mpesa/callback" 
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
