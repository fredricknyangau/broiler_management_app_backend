from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/broiler_farm"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Application
    APP_NAME: str = "Broiler Farm Management API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Notifications (for future implementation)
    SMS_PROVIDER_API_KEY: Optional[str] = None
    EMAIL_API_KEY: Optional[str] = None
    PUSH_NOTIFICATION_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()