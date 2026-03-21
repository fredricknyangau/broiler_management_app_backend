from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user, check_enterprise_subscription
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
