"""admin/config.py — System configuration and audit log endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from typing import List, Optional, Any, Generic, TypeVar
from pydantic import BaseModel

from app.api.deps import get_db, get_current_admin_user
from app.db.models.user import User
from app.db.models.config import SystemConfig
from app.db.models.audit import AuditLog
from app.schemas.config import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import log_action

router = APIRouter()

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    total_pages: int
    current_page: int


# ── System Config ────────────────────────────────────────────────────────────

_DEFAULT_CONFIGS = {
    "MAINTENANCE_MODE": "false",
    "REGISTRATION_OPEN": "true",
    "GLOBAL_BANNER": "",
}


@router.get("/config", response_model=List[SystemConfigResponse])
async def get_system_configs(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all system configurations (Admin only)."""
    result = await db.execute(select(SystemConfig))
    configs = list(result.scalars().all())

    existing_keys = {c.key for c in configs}
    added_new = False
    for key, val in _DEFAULT_CONFIGS.items():
        if key not in existing_keys:
            new_conf = SystemConfig(key=key, value=val, category="system", is_encrypted=False)
            db.add(new_conf)
            configs.append(new_conf)
            added_new = True

    if added_new:
        await db.commit()

    return configs


@router.post("/config", response_model=SystemConfigResponse)
async def create_or_update_config(
    config_in: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Create or update a configuration key."""
    result = await db.execute(select(SystemConfig).filter(SystemConfig.key == config_in.key))
    existing = result.scalars().first()

    if existing:
        for field, value in config_in.model_dump(exclude={"key"}).items():
            setattr(existing, field, value)
        db_obj = existing
        action = "UPDATE_CONFIG"
    else:
        db_obj = SystemConfig(**config_in.model_dump())
        db.add(db_obj)
        action = "CREATE_CONFIG"

    await db.commit()
    await db.refresh(db_obj)

    await log_action(db, action, current_admin.id, "SystemConfig", str(db_obj.id), {"key": config_in.key})
    return db_obj


# ── Audit Logs ───────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get system audit logs (Admin only)."""
    from sqlalchemy import func

    query = select(AuditLog).options(joinedload(AuditLog.user))
    if search:
        query = query.join(User, isouter=True).filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                AuditLog.resource_type.ilike(f"%{search}%"),
            )
        )

    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(
        query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    )
    logs = result.scalars().all()

    for log in logs:
        if log.user:
            log.user_email = log.user.email

    return PaginatedResponse(
        items=logs,
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1,
    )
