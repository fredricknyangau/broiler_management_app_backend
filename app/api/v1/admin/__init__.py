"""
app/api/v1/admin/__init__.py — Admin sub-router package.

Mounts all admin sub-routers under a single admin router.
"""

from fastapi import APIRouter

from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.billing import router as billing_router
from app.api.v1.admin.config import router as config_router
from app.api.v1.admin.users import router as users_router

router = APIRouter()

router.include_router(users_router, tags=["Admin - Users"])
router.include_router(billing_router, tags=["Admin - Billing"])
router.include_router(config_router, tags=["Admin - Config"])
router.include_router(analytics_router, tags=["Admin - Analytics"])

__all__ = [
    "router",
    "users_router",
    "billing_router",
    "config_router",
    "analytics_router",
]
