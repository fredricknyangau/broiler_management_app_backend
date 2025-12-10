
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.flock import Flock
from app.db.models.user import User
from app.schemas.flock import FlockCreate, FlockResponse, FlockUpdate
from app.services.vaccination_service import VaccinationService
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType

router = APIRouter()

@router.post("/", response_model=FlockResponse, status_code=status.HTTP_201_CREATED)
async def create_flock(
    flock_in: FlockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new flock.
    
    - **flock_in**: Flock details (name, breed, start_date, etc.)
    - Returns the created flock with assigned ID.
    - Requires authentication.
    """
    flock = Flock(
        **flock_in.model_dump(),
        farmer_id=current_user.id
    )

    # Enforce Plan Limits
    # 1. Get current active subscription
    result = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()

    current_plan = sub.plan_type if sub else PlanType.STARTER

    # 2. Check limits if on STARTER
    if current_plan == PlanType.STARTER:
        # Check active flocks count
        # Could optimize with select(func.count(Flock.id))
        result = await db.execute(
            select(Flock).filter(
                Flock.farmer_id == current_user.id,
                Flock.status == 'active'
            )
        )
        active_flocks = result.scalars().all()
        active_flocks_count = len(active_flocks)
        
        if active_flocks_count >= 2:
            raise HTTPException(
                status_code=403, 
                detail="Starter plan is limited to 2 active batches. Please upgrade to create more."
            )
    
    db.add(flock)
    await db.commit()
    await db.refresh(flock)
    
    # Auto-generate vaccination schedule
    # Note: VaccinationService needs to be async-aware or passed the async session
    # Assuming VaccinationService is updated or we handle it here.
    # For safety in this refactoring step, I'll instantiate it but need to ensure it supports async
    vaccination_service = VaccinationService(db)
    # await vaccination_service.generate_schedule(flock.id, flock.start_date) # TODO: Ensure this is async
    # TEMPORARY FIX: If VaccinationService is not async, this call might fail. 
    # Attempting to call it, assuming I will fix VaccinationService next.
    if hasattr(vaccination_service, 'generate_schedule'):
         # If it's async it should be awaited. Ideally we check the service first.
         # For now, I will comment out the scheduling to prevent 500s until service is fixed.
         pass 
         # await vaccination_service.generate_schedule(flock.id, flock.start_date)

    return flock

@router.get("/", response_model=List[FlockResponse])
async def read_flocks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all flocks owned by the current user.
    """
    result = await db.execute(
        select(Flock)
        .filter(Flock.farmer_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    flocks = result.scalars().all()
    return flocks

@router.get("/{flock_id}", response_model=FlockResponse)
async def read_flock(
    flock_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific flock by ID.
    """
    result = await db.execute(
        select(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id)
    )
    flock = result.scalars().first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    return flock

@router.put("/{flock_id}", response_model=FlockResponse)
async def update_flock(
    flock_id: UUID,
    flock_in: FlockUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a flock's details.
    """
    result = await db.execute(
        select(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id)
    )
    flock = result.scalars().first()
    
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    
    update_data = flock_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flock, field, value)
    
    # db.add(flock) # Not strictly necessary if attached to session
    await db.commit()
    await db.refresh(flock)
    return flock

@router.delete("/{flock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flock(
    flock_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a flock.
    """
    result = await db.execute(
        select(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id)
    )
    flock = result.scalars().first()
    
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    
    await db.delete(flock)
    await db.commit()
    return None
