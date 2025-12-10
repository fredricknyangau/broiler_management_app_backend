from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List, Optional
from app.api.deps import get_db, get_current_admin_user
from app.db.models.audit import AuditLog
from app.db.models.user import User
from app.schemas.audit import AuditLogResponse

router = APIRouter()

@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get system audit logs (Admin only).
    """
    stmt = select(AuditLog).options(joinedload(AuditLog.user))
    
    if action:
        stmt = stmt.filter(AuditLog.action == action)
    if user_id:
        stmt = stmt.filter(AuditLog.user_id == user_id)
        
    result = await db.execute(stmt.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit))
    logs = result.scalars().all()
    
    # Enrich with user email 
    results = []
    for log in logs:
        log_resp = AuditLogResponse.model_validate(log)
        if log.user:
            log_resp.user_email = log.user.email
        results.append(log_resp)
        
    return results
