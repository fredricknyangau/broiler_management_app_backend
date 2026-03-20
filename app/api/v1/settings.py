from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.user_setting import UserSetting
from app.schemas.user_setting import UserSettingResponse, UserSettingUpdate

router = APIRouter()

@router.get("/", response_model=List[UserSettingResponse])
async def read_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List current user settings."""
    stmt = select(UserSetting).filter(UserSetting.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/{key}", response_model=UserSettingResponse)
async def update_setting(
    key: str,
    setting_in: UserSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a specific setting."""
    stmt = select(UserSetting).filter(UserSetting.user_id == current_user.id, UserSetting.key == key)
    result = await db.execute(stmt)
    setting = result.scalars().first()
    
    if not setting:
        setting = UserSetting(user_id=current_user.id, key=key, value=setting_in.value, category=setting_in.category or "general")
        db.add(setting)
    else:
        setting.value = setting_in.value
        if setting_in.category:
            setting.category = setting_in.category
            
    await db.commit()
    await db.refresh(setting)
    return setting
