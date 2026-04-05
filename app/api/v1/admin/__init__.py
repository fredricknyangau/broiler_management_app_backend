"""
app/api/v1/admin/__init__.py — Admin sub-router package.

Import from sub-modules here for use in app/api/v1/admin.py (the router that
mounts under /admin in main.py).
"""
from app.api.v1.admin.users import router as users_router
from app.api.v1.admin.billing import router as billing_router
from app.api.v1.admin.config import router as config_router
from app.api.v1.admin.analytics import router as analytics_router

__all__ = ["users_router", "billing_router", "config_router", "analytics_router"]
