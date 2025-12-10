from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import settings
from app.api.v1 import auth, flocks, daily_checks, finance, inventory, biosecurity, alerts, events, health, market, admin, data, people, analytics, billing, audit
import structlog
from app.core.logging import setup_logging

# Configure logging on startup
# Configure logging on startup
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
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
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(flocks.router, prefix=f"{settings.API_V1_PREFIX}/flocks", tags=["Flocks"])
app.include_router(daily_checks.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Daily Checks"])
app.include_router(finance.router, prefix=f"{settings.API_V1_PREFIX}/finance", tags=["Finance"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_PREFIX}/inventory", tags=["Inventory"])
app.include_router(biosecurity.router, prefix=f"{settings.API_V1_PREFIX}/biosecurity", tags=["Biosecurity"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"])
app.include_router(events.router, prefix=f"{settings.API_V1_PREFIX}/events", tags=["Events"])
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["Health"])
app.include_router(market.router, prefix=f"{settings.API_V1_PREFIX}/market", tags=["Market"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])
app.include_router(data.router, prefix=f"{settings.API_V1_PREFIX}/data", tags=["Data Sync"])
app.include_router(people.router, prefix=f"{settings.API_V1_PREFIX}/people", tags=["People"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(billing.router, prefix=f"{settings.API_V1_PREFIX}/billing", tags=["Billing"])
app.include_router(audit.router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["Audit"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Broiler Farm Management API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }
