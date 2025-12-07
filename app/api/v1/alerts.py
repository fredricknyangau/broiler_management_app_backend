from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.db.models.alert import Alert
from app.db.models.user import User
from app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
def read_alerts(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    flock_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve alerts.
    
    - **status**: Filter by status (active, acknowledged, resolved)
    - **flock_id**: Filter by specific flock
    """
    query = db.query(Alert).join(Alert.flock).filter(Alert.flock.has(farmer_id=current_user.id))
    
    if status:
        query = query.filter(Alert.status == status)
    if flock_id:
        query = query.filter(Alert.flock_id == flock_id)
        
    return query.order_by(Alert.triggered_at.desc()).offset(skip).limit(limit).all()

@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: UUID,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update alert status.
    
    - Automatically sets `acknowledged_at` or `resolved_at` timestamps based on status change.
    """
    alert = db.query(Alert).join(Alert.flock).filter(
        Alert.id == alert_id,
        Alert.flock.has(farmer_id=current_user.id)
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    update_data = alert_update.model_dump(exclude_unset=True)
    if 'status' in update_data:
        if update_data['status'] == 'acknowledged' and not alert.acknowledged_at:
            alert.acknowledged_at = datetime.utcnow()
        elif update_data['status'] == 'resolved' and not alert.resolved_at:
            alert.resolved_at = datetime.utcnow()
            
    for field, value in update_data.items():
        setattr(alert, field, value)
        
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
