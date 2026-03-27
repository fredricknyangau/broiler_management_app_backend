from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user, check_enterprise_subscription, get_current_non_viewer
from app.db.models.farm import Farm
from app.db.models.user import User
from app.schemas.farm import FarmCreate, FarmResponse, FarmUpdate

router = APIRouter(dependencies=[Depends(check_enterprise_subscription)])

@router.get("/", response_model=List[FarmResponse])
async def list_farms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all farms owned by the current authenticated user.
    """
    result = await db.execute(select(Farm).where(Farm.owner_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    farm_in: FarmCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer)
):
    """
    Create a new farm profile for multi-location management.
    """
    farm = Farm(
        name=farm_in.name,
        location=farm_in.location,
        owner_id=current_user.id
    )
    db.add(farm)
    await db.commit()
    await db.refresh(farm)
    return farm

@router.put("/{farm_id}", response_model=FarmResponse)
async def update_farm(
    farm_id: UUID,
    farm_in: FarmUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer)
):
    """
    Update existing farm details layout parameters.
    """
    result = await db.execute(select(Farm).where(Farm.id == farm_id, Farm.owner_id == current_user.id))
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or access denied")

    if farm_in.name is not None:
        farm.name = farm_in.name
    if farm_in.location is not None:
        farm.location = farm_in.location
    if farm_in.is_active is not None:
        farm.is_active = farm_in.is_active

    await db.commit()
    await db.refresh(farm)
    return farm

@router.post("/{farm_id}/members", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_farm_member(
    farm_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer)
):
    """
    Add a manager or viewer (User) to a specific Farm Profile.
    Only the Farm Owner or Admin can manage memberships.
    """
    from app.db.models.farm_member import FarmMember

    # 1. Verify Farm Ownership
    result = await db.execute(select(Farm).where(Farm.id == farm_id))
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
        
    if farm.owner_id != current_user.id and current_user.role != "ADMIN":
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the Farm Owner can manage members.")

    # 2. Add Link
    # Check if already a member to prevent duplicates
    exists = await db.execute(select(FarmMember).where(FarmMember.farm_id == farm_id, FarmMember.user_id == user_id))
    if exists.scalar_one_or_none():
         return {"status": "success", "message": "Already a member"}

    member = FarmMember(farm_id=farm_id, user_id=user_id)
    db.add(member)
    await db.commit()
    return {"status": "success", "message": "Member added to farm"}


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm(
    farm_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer)
):
    """
    Delete a farm profile. Only the owner can delete.
    """
    result = await db.execute(select(Farm).where(Farm.id == farm_id, Farm.owner_id == current_user.id))
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or access denied")
        
    await db.delete(farm)
    await db.commit()
    return None

