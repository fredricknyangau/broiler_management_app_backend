from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.alert import Alert
from pydantic import BaseModel

router = APIRouter()

@router.get("/")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get alerts for current user. Admins get all.
    """
    if current_user.role == "ADMIN":
        query = select(Alert)
    else:
        query = select(Alert).filter(
            or_(
                Alert.user_id == current_user.id,
                Alert.user_id == None
            )
        )
        
    result = await db.execute(query.order_by(Alert.triggered_at.desc()))
    return result.scalars().all()

@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark alert as acknowledged.
    """
    result = await db.execute(select(Alert).filter(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if current_user.role != "ADMIN" and str(alert.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to acknowledge this alert")
        
    alert.status = "acknowledged"
    await db.commit()
    return {"status": "success"}

class BroadcastCreate(BaseModel):
    title: str
    message: str
    severity: str = "info" # low, medium, high, critical

@router.post("/broadcast")
async def broadcast_alert(
    payload: BroadcastCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user) # Assuming Admin verify later
):
    """
    Broadcast a global system alert/announcement to all users. (Admin only)
    """
    if current_admin.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can broadcast alerts")

    from app.db.models.alert import Alert as AlertModel # fix circular reference if any
    alert = Alert(
        title=payload.title,
        message=payload.message,
        alert_type="broadcast",
        severity=payload.severity,
        user_id=None
    )
    db.add(alert)
    await db.commit()
    return {"status": "success", "alert_id": alert.id}
