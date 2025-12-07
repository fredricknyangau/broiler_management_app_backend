from pydantic import BaseModel, UUID4, Field, Json
from datetime import datetime
from typing import Optional, Dict, Any

class AlertBase(BaseModel):
    """Base fields for Alert."""
    flock_id: UUID4
    alert_type: str
    severity: str
    title: str
    message: str
    status: str = "active"
    alert_metadata: Optional[Dict[str, Any]] = None

class AlertCreate(AlertBase):
    """Schema for creating an alert (system or manual)."""
    pass

class AlertUpdate(BaseModel):
    """Schema for updating alert status."""
    status: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class AlertResponse(AlertBase):
    """Schema for alert response."""
    id: UUID4
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
