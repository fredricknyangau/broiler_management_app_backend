from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    """Base properties shared by create, update, and response schemas."""

    name: str = Field(..., max_length=255, description="Name of the farm location")
    location: Optional[str] = Field(
        None, max_length=255, description="Optional address or geographic details"
    )
    is_active: bool = Field(True, description="Status flag for active management")


class FarmCreate(BaseModel):
    """Properties to receive on farm creation."""

    name: str = Field(..., max_length=255)
    location: Optional[str] = Field(None, max_length=255)


class FarmUpdate(BaseModel):
    """Properties to receive on farm update."""

    name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class FarmResponse(FarmBase):
    """Properties to return to client."""

    id: UUID4
    owner_id: UUID4
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
