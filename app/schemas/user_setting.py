from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserSettingBase(BaseModel):
    key: str
    value: Optional[str] = None
    category: str = "general"

class UserSettingCreate(UserSettingBase):
    pass

class UserSettingUpdate(BaseModel):
    value: Optional[str] = None
    category: Optional[str] = None

class UserSettingResponse(UserSettingBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
