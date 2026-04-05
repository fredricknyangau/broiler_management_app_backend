"""admin/users.py — User management endpoints (list, update, delete)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_
from typing import List, Any, Optional, Generic, TypeVar
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_admin_user
from app.db.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.audit_service import log_action

router = APIRouter()

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    total_pages: int
    current_page: int


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all users with pagination and search."""
    query = select(User)
    if search:
        query = query.filter(
            or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%"))
        )

    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_res.scalar() or 0

    result = await db.execute(query.order_by(User.created_at.desc()).offset(skip).limit(limit))
    users = result.scalars().all()

    return PaginatedResponse(
        items=users,
        total_count=total_count,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1,
        current_page=(skip // limit) + 1 if limit > 0 else 1,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's status or role (Admin only)."""
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    await log_action(
        db=db,
        action="UPDATE_USER",
        user_id=current_admin.id,
        resource_type="User",
        resource_id=str(user.id),
        details=update_data,
    )
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (Admin only)."""
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    await db.delete(user)
    await db.commit()

    await log_action(
        db=db,
        action="DELETE_USER",
        user_id=current_admin.id,
        resource_type="User",
        resource_id=str(user_id),
    )
    return {"message": "User deleted successfully"}

