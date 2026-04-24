from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://broiler_user:broiler_pass@localhost:5432/broiler_farm_db"
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Ensure the URL uses the asyncpg driver and strips incompatible options."""
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

        parsed = urlparse(url)
        qsl = parse_qsl(parsed.query)

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
        ssl_indicators = [
            "sslmode=require",
            "sslmode=verify-full",
            "sslmode=verify-ca",
            "channel_binding=require",
            "neon.tech",
        ]
        if any(indicator in self.DATABASE_URL for indicator in ssl_indicators):
            args["ssl"] = True
        return args

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Application
    APP_NAME: str = "Broiler Farm Management API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Notifications
    SMS_PROVIDER_API_KEY: Optional[str] = None
    AFRICASTALKING_USERNAME: str = "sandbox"
    AFRICASTALKING_API_KEY: str = "place_holder"
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
    # Defaults to sandbox — set to https://api.safaricom.co.ke in production .env
    MPESA_BASE_URL: str = "https://sandbox.safaricom.co.ke"

    # AI Integration
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # OAuth / SSO
    GOOGLE_CLIENT_ID: Optional[str] = None  # From GCP Console
    APPLE_CLIENT_ID: Optional[str] = None  # Apple Service ID (e.g. com.kukufiti.app)
    APPLE_TEAM_ID: Optional[str] = None  # 10-char Apple Team ID
    APPLE_KEY_ID: Optional[str] = None  # Key ID from Apple Developer Portal

    # ────────────────────────────────────────────────────────────────
    # MONITORING & ERROR TRACKING
    # ────────────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None  # Sentry error tracking
    SENTRY_ENABLED: bool = False  # Enable Sentry monitoring
    SENTRY_TRACES_SAMPLE_RATE: float = (
        0.1  # Sample 10% of transactions (performance monitoring)
    )

    # ────────────────────────────────────────────────────────────────
    # SECURITY VALIDATORS
    # ────────────────────────────────────────────────────────────────

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure SECRET_KEY is not the default placeholder in production."""
        if not v or v == "change-me-in-production":
            raise ValueError(
                "❌ SECURITY ERROR: SECRET_KEY must be set via environment variable\n"
                "   Do not use the default 'change-me-in-production' in production\n"
                "   Generate a secure key: python3 scripts/generate_secret.py"
            )
        if len(v) < 32:
            raise ValueError("❌ SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure DATABASE_URL is configured."""
        if not v:
            raise ValueError(
                "❌ DATABASE_URL environment variable is required\n"
                "   Set it in .env: DATABASE_URL=postgresql+asyncpg://..."
            )
        if "broiler_pass" in v and not any(
            host in v for host in ["localhost", "@postgres:"]
        ):
            raise ValueError(
                "❌ SECURITY WARNING: Using default database credentials in production is not allowed\n"
                "   Use production database credentials in DATABASE_URL"
            )
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_mode(cls, v):
        """Warn if DEBUG is True in production environment."""
        if v is True:
            import os

            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(
                    "❌ DEBUG=True detected in production!\n"
                    "   Set DEBUG=False in production environment variables"
                )
        return v


settings = Settings()
