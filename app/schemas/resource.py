from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ResourceBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: str
    category: str = "general"
    icon: Optional[str] = None


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None


class ResourceResponse(ResourceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
