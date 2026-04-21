"""
app/api/v1/admin.py — Admin module master router.

This replaces the old 775-line monolithic admin router. All endpoints have been
split into domain-specific sub-routers in `app/api/v1/admin/`.
"""

from fastapi import APIRouter

from app.api.v1.admin import (analytics_router, billing_router, config_router,
                              users_router)

router = APIRouter()

# Include sub-routers. The prefix and tags are set in main.py, but we can organize them here if needed.
# Since main.py usually sets prefix="/admin" and tags=["Admin"] when including this router,
# we just mount directly.

router.include_router(users_router)
router.include_router(billing_router)
router.include_router(config_router)
router.include_router(analytics_router)
