from datetime import datetime, timezone

import redis.asyncio as redis
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
except ImportError:  # pragma: no cover - optional dependency in local/dev environments
    sentry_sdk = None
    FastApiIntegration = None
    SqlalchemyIntegration = None

from app.api.v1 import (admin, ai, alerts, analytics, api_keys, audit, auth,
                        billing, biosecurity, community, daily_checks, data,
                        events, farms, finance, flocks, health, inventory,
                        market, people, resources)
from app.api.v1 import settings as settings_router
from app.api.v1 import tasks
from app.config import settings
from app.core.logging import setup_logging
from app.db.session import engine

# Configure logging on startup
setup_logging()

# Initialize Sentry for error tracking and performance monitoring
if settings.SENTRY_ENABLED and settings.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        traces_sampler=lambda ctx: (
            0.0
            if ctx["transaction"].startswith("/health")
            else settings.SENTRY_TRACES_SAMPLE_RATE
        ),
        send_default_pii=False,
        environment="production" if not settings.DEBUG else "development",
    )
    logger = structlog.get_logger()
    logger.info("sentry_initialized", dsn_prefix=settings.SENTRY_DSN[:30])

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Modern Poultry Farm Management System API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Auth endpoints (login, register, SSO)",
        },
        {"name": "Flocks", "description": "Flock/batch management"},
        {"name": "Farms", "description": "Farm management"},
        {"name": "Daily Checks", "description": "Daily observations and checks"},
        {"name": "Finance", "description": "Financial tracking (expenses, sales)"},
        {"name": "Inventory", "description": "Stock and inventory management"},
        {"name": "Biosecurity", "description": "Biosecurity protocols and logs"},
        {"name": "Alerts", "description": "Alert rules and notifications"},
        {
            "name": "Events",
            "description": "Event logging (mortality, feed, vaccination, weight)",
        },
        {"name": "People", "description": "Staff and team management"},
        {"name": "Analytics", "description": "Analytics and reporting"},
        {"name": "Billing", "description": "Billing, subscriptions, and payments"},
        {"name": "AI Advisory", "description": "AI-powered advisory services"},
        {"name": "Community", "description": "Community features (posts, comments)"},
        {"name": "Admin", "description": "Admin operations"},
        {"name": "Health", "description": "Health check endpoints"},
    ],
)


@app.on_event("startup")
async def startup_event():
    logger = structlog.get_logger()
    logger.info("application_started", environment="production")


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(
    auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"]
)
app.include_router(
    flocks.router, prefix=f"{settings.API_V1_PREFIX}/flocks", tags=["Flocks"]
)
app.include_router(
    farms.router, prefix=f"{settings.API_V1_PREFIX}/farms", tags=["Farms"]
)
app.include_router(
    daily_checks.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Daily Checks"]
)
app.include_router(
    finance.router, prefix=f"{settings.API_V1_PREFIX}/finance", tags=["Finance"]
)
app.include_router(
    inventory.router, prefix=f"{settings.API_V1_PREFIX}/inventory", tags=["Inventory"]
)
app.include_router(
    biosecurity.router,
    prefix=f"{settings.API_V1_PREFIX}/biosecurity",
    tags=["Biosecurity"],
)
app.include_router(
    alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"]
)
app.include_router(
    api_keys.router, prefix=f"{settings.API_V1_PREFIX}/api-keys", tags=["API Keys"]
)
app.include_router(
    events.router, prefix=f"{settings.API_V1_PREFIX}/events", tags=["Events"]
)
app.include_router(
    health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["Health"]
)
app.include_router(
    market.router, prefix=f"{settings.API_V1_PREFIX}/market", tags=["Market"]
)
app.include_router(
    admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"]
)
app.include_router(
    data.router, prefix=f"{settings.API_V1_PREFIX}/data", tags=["Data Sync"]
)
app.include_router(
    people.router, prefix=f"{settings.API_V1_PREFIX}/people", tags=["People"]
)
app.include_router(
    analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"]
)
app.include_router(
    billing.router, prefix=f"{settings.API_V1_PREFIX}/billing", tags=["Billing"]
)
app.include_router(
    audit.router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["Audit"]
)
app.include_router(
    resources.router, prefix=f"{settings.API_V1_PREFIX}/resources", tags=["Resources"]
)
app.include_router(
    settings_router.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["Settings"],
)
app.include_router(
    tasks.router, prefix=f"{settings.API_V1_PREFIX}/tasks", tags=["Tasks"]
)
app.include_router(
    ai.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI Advisory"]
)
app.include_router(
    community.router, prefix=f"{settings.API_V1_PREFIX}/community", tags=["Community"]
)


@app.get("/")
async def root():
    """Root endpoint - API information and links

    Returns basic API information and links to documentation.
    """
    return {
        "message": "🐔 Broiler Farm Management API",
        "status": "running",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "redoc": f"{settings.API_V1_PREFIX}/redoc",
        "openapi": f"{settings.API_V1_PREFIX}/openapi.json",
        "health": f"{settings.API_V1_PREFIX}/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint

    Returns the health status of the API and its dependencies.

    Returns:
        - status: Overall API status (healthy/unhealthy)
        - database: Database connection status
        - redis: Redis connection status
        - timestamp: Server timestamp
    """
    database_status = "connected"
    redis_status = "connected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        database_status = "disconnected"

    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.aclose()
    except Exception:
        redis_status = "disconnected"

    overall_status = (
        "healthy"
        if database_status == "connected" and redis_status == "connected"
        else "degraded"
    )
    return {
        "status": overall_status,
        "database": database_status,
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "production" if not settings.DEBUG else "development",
    }
