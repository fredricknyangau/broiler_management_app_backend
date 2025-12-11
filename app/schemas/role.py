from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID

class RoleBase(BaseModel):
    name: str = Field(..., description="Unique name of the role (e.g., ADMIN, MANAGER)")
    description: Optional[str] = None
    permissions: Dict[str, bool] = Field(default_factory=dict, description="Map of permission keys to boolean values")

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
