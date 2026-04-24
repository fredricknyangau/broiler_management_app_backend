import hashlib
import secrets
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (check_enterprise_subscription, get_current_user,
                          get_db)
from app.db.models.api_key import ApiKey
from app.db.models.user import User

router = APIRouter()


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    raw_key: str


@router.get("/", response_model=List[ApiKeyResponse])
async def get_api_keys(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    List active API Key prefixes for the user.
    """
    result = await db.execute(select(ApiKey).filter(ApiKey.user_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=ApiKeyCreateResponse)
async def create_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    is_enterprise: bool = Depends(check_enterprise_subscription),
):
    """
    Generate a new API Key for Enterprise access nodes.
    """
    if not is_enterprise and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="API Access Key Generation is an Enterprise feature.",
        )

    raw_key = f"kf_{secrets.token_hex(24)}"
    key_prefix = raw_key[:10]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=current_user.id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )
