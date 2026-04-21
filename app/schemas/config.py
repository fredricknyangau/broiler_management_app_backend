from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SystemConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    category: str = "general"
    is_encrypted: bool = False


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    category: Optional[str] = None
    is_encrypted: Optional[bool] = None


class SystemConfigResponse(SystemConfigBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
