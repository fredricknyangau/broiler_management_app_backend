import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # pydantic-settings v2: OS env vars always take precedence over .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://broiler_user:broiler_pass@localhost:5432/broiler_farm_db"

@property
def ASYNC_DATABASE_URL(self) -> str:
    """Ensure the URL uses the asyncpg driver and strips incompatible options."""
    from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

    url = self.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    qsl = parse_qsl(parsed.query)

    # Full list of libpq/psycopg2 parameters asyncpg does not accept
    incompatible_args = {
        "sslmode",
        "channel_binding",
        "connect_timeout",
        "application_name",
        "options",
        "target_session_attrs",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslcrl",
        "gssencmode",
        "krbsrvname",
    }

    filtered_qsl = [(k, v) for k, v in qsl if k not in incompatible_args]
    rebuilt = parsed._replace(query=urlencode(filtered_qsl))
    return urlunparse(rebuilt)

@property
def ASYNC_CONNECT_ARGS(self) -> dict:
    """Returns connect args conditionally."""
    args = {}

    # Check all the ways SSL can be signalled in a connection string
    ssl_indicators = [
        "sslmode=require",
        "sslmode=verify-full",
        "sslmode=verify-ca",
        "channel_binding=require",
        "neon.tech",        # Neon always requires SSL
    ]

    if any(indicator in self.DATABASE_URL for indicator in ssl_indicators):
        args["ssl"] = True

    return args

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
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
    MPESA_SHORTCODE: str = "174379"
    MPESA_CALLBACK_URL: str = "https://your-domain.com/api/v1/billing/mpesa/callback"

    # AI Integration
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"


settings = Settings()

