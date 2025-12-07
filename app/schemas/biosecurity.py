from pydantic import BaseModel, Field, UUID4, Json
from datetime import date
from typing import Optional, List, Dict, Any

class BiosecurityCheckBase(BaseModel):
    """Base fields for Biosecurity Check."""
    date: date
    items: List[Dict[str, Any]] # List of {task, completed, notes}
    notes: Optional[str] = None
    completed_by: Optional[str] = None

class BiosecurityCheckCreate(BiosecurityCheckBase):
    """Schema for submitting a biosecurity record."""
    pass

class BiosecurityCheckUpdate(BaseModel):
    """Schema for updating a biosecurity record."""
    date: Optional[date] = None
    items: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    completed_by: Optional[str] = None

class BiosecurityCheckResponse(BiosecurityCheckBase):
    """Schema for biosecurity response."""
    id: UUID4
    farmer_id: UUID4
    
    class Config:
        from_attributes = True
