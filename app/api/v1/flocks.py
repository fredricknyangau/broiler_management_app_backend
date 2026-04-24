from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (get_current_non_viewer, get_current_user, get_db)
from app.db.models.flock import Flock
from app.db.models.subscription import (PlanType, Subscription,
                                        SubscriptionStatus)
from app.db.models.user import User
from app.schemas.flock import FlockCreate, FlockResponse, FlockUpdate
from app.services.finance_service import FinanceService
from app.services.vaccination_service import VaccinationService

router = APIRouter()


@router.post("/", response_model=FlockResponse, status_code=status.HTTP_201_CREATED)
async def create_flock(
    flock_in: FlockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """
    Create a new flock.

    - **flock_in**: Flock details (name, breed, start_date, etc.)
    - Returns the created flock with assigned ID.
    - Requires authentication.
    """
    flock = Flock(**flock_in.model_dump(), farmer_id=current_user.id)

    # Enforce Plan Limits
    # 1. Get current active subscription
    result = await db.execute(
        select(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()

    current_plan = sub.plan_type if sub else PlanType.STARTER

    # Admins and Superusers bypass subscription locks
    if current_user.role == "ADMIN" or getattr(current_user, "is_superuser", False):
        current_plan = PlanType.ENTERPRISE

    # 2. Check limits if on STARTER
    if current_plan == PlanType.STARTER:
        # Check total birds count in active flocks
        result = await db.execute(
            select(Flock).filter(
                Flock.farmer_id == current_user.id, Flock.status == "active"
            )
        )
        active_flocks = result.scalars().all()
        total_birds = (
            sum(f.initial_count for f in active_flocks) + flock_in.initial_count
        )

        if len(active_flocks) >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Starter Plan is limited to a Single Active Flock (Single Batch Production). Upgrade to Professional for unlimited batches.",
            )

        if total_birds > 100:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Starter plan is limited to 100 birds total. You currently have {total_birds - flock_in.initial_count} active birds. Adding {flock_in.initial_count} exceeds the limit.",
            )

    db.add(flock)
    await db.commit()
    await db.refresh(flock)

    # Auto-generate standard vaccination schedule for the new flock
    vaccination_service = VaccinationService(db)
    await vaccination_service.generate_schedule(flock.id, flock.start_date)

    # Auto-record acquisition cost as expenditure
    if flock.cost_per_bird and flock.cost_per_bird > 0:
        total_cost = float(flock.cost_per_bird) * flock.initial_count
        finance_service = FinanceService(db)
        await finance_service.sync_expenditure(
            farmer_id=current_user.id,
            amount=total_cost,
            category="chick_acquisition",
            description=f"Chick placement: {flock.initial_count} birds @ KSh {flock.cost_per_bird} each — {flock.name}",
            date=flock.start_date,
            flock_id=flock.id,
            related_id=flock.id,
            related_type="flock_placement",
        )
        await db.commit()

    return flock


@router.get("/", response_model=List[FlockResponse])
async def read_flocks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_non_viewer),
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

    await db.commit()
    await db.refresh(flock)

    # Re-sync flock placement expenditure if cost fields changed
    if "cost_per_bird" in update_data or "initial_count" in update_data:
        if flock.cost_per_bird and flock.cost_per_bird > 0:
            total_cost = float(flock.cost_per_bird) * flock.initial_count
            finance_service = FinanceService(db)
            await finance_service.sync_expenditure(
                farmer_id=current_user.id,
                amount=total_cost,
                category="chick_acquisition",
                description=f"Chick placement: {flock.initial_count} birds @ KSh {flock.cost_per_bird} each — {flock.name}",
                date=flock.start_date,
                flock_id=flock.id,
                related_id=flock.id,
                related_type="flock_placement",
            )
            await db.commit()

    return flock


@router.delete("/{flock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flock(
    flock_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
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
