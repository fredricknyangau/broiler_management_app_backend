from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date
from typing import Optional

class ScheduledTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: date
    status: str = "PENDING"
    category: str = "general"
    flock_id: Optional[UUID] = None

class ScheduledTaskCreate(ScheduledTaskBase):
    pass

class ScheduledTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    category: Optional[str] = None
    flock_id: Optional[UUID] = None

class ScheduledTaskResponse(ScheduledTaskBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
