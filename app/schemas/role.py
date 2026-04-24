from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(..., description="Unique name of the role (e.g., ADMIN, MANAGER)")
    description: Optional[str] = None
    permissions: Dict[str, bool] = Field(
        default_factory=dict, description="Map of permission keys to boolean values"
    )


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None


class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
