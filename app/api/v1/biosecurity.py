from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.biosecurity import BiosecurityCheck
from app.db.models.user import User
from app.schemas.biosecurity import BiosecurityCheckCreate, BiosecurityCheckResponse, BiosecurityCheckUpdate

router = APIRouter()

@router.post("/", response_model=BiosecurityCheckResponse, status_code=status.HTTP_201_CREATED)
async def create_biosecurity_check(
    check_in: BiosecurityCheckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Log a biosecurity compliance check.
    """
    check = BiosecurityCheck(**check_in.model_dump(), farmer_id=current_user.id)
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check

@router.get("/", response_model=List[BiosecurityCheckResponse])
async def read_biosecurity_checks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List biosecurity checks.
    """
    result = await db.execute(
        select(BiosecurityCheck)
        .filter(BiosecurityCheck.farmer_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.put("/{check_id}", response_model=BiosecurityCheckResponse)
async def update_biosecurity_check(
    check_id: UUID,
    check_in: BiosecurityCheckUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a biosecurity record.
    """
    result = await db.execute(select(BiosecurityCheck).filter(BiosecurityCheck.id == check_id, BiosecurityCheck.farmer_id == current_user.id))
    check = result.scalars().first()
    if not check:
        raise HTTPException(status_code=404, detail="Biosecurity record not found")
    
    update_data = check_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(check, field, value)
    
    # db.add(check)
    await db.commit()
    await db.refresh(check)
    return check

@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_biosecurity_check(
    check_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a biosecurity record.
    """
    result = await db.execute(select(BiosecurityCheck).filter(BiosecurityCheck.id == check_id, BiosecurityCheck.farmer_id == current_user.id))
    check = result.scalars().first()
    if not check:
        raise HTTPException(status_code=404, detail="Biosecurity record not found")
    
    await db.delete(check)
    await db.commit()
    return None
