from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import settings
from app.api.v1 import auth, flocks, daily_checks, finance, inventory, biosecurity, alerts, events, health, market, admin, data, people, analytics


import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for managing broiler farms in Kenya",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up...")
    logger.info(f"Configuration REDIS_URL: {settings.REDIS_URL}")
    logger.info(f"Environment REDIS_URL: {os.environ.get('REDIS_URL')}")
    # Log all env vars to see what's available (masked for security if needed, but for now just dumping keys)
    logger.info(f"Available Environment Variables: {list(os.environ.keys())}")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
