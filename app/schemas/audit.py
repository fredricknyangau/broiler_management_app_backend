from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogBase(BaseModel):
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    user_id: Optional[UUID] = None


class AuditLogResponse(AuditLogBase):
    id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None  # Helper for frontend display
    timestamp: datetime

    class Config:
        from_attributes = True
