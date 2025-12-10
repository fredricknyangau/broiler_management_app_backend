from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditLog
from typing import Dict, Any, Optional
from uuid import UUID

async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """
    Log an audit event.
    """
    try:
        log_entry = AuditLog(
            user_id=str(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address
        )
        db.add(log_entry)
        await db.commit()
    except Exception as e:
        print(f"Failed to write audit log: {e}")
        await db.rollback()
