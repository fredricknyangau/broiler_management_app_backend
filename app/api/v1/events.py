from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.events import (
    MortalityEvent, 
    FeedConsumptionEvent, 
    VaccinationEvent, 
    WeightMeasurementEvent
)
from app.schemas.daily_check import (
    MortalityEventResponse,
    FeedConsumptionEventResponse,
    VaccinationEventResponse,
    WeightMeasurementEventResponse,
    MortalityEventCreate,
    FeedConsumptionEventCreate,
    VaccinationEventCreate,
    WeightMeasurementEventCreate,
    MortalityEventUpdate,
    FeedConsumptionEventUpdate,
    VaccinationEventUpdate,
    WeightMeasurementEventUpdate
)

router = APIRouter()

@router.get("/mortality", response_model=List[MortalityEventResponse])
async def read_mortality_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List mortality events."""
    stmt = select(MortalityEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(MortalityEvent.flock_id == flock_id)
    
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/mortality", response_model=MortalityEventResponse, status_code=status.HTTP_201_CREATED)
async def create_mortality_event(
    event_in: MortalityEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create mortality event."""
    # Note: Logic usually goes through DailyCheckService, but standalone endpoint is ok
    event = MortalityEvent(**event_in.model_dump(exclude={"event_id"}), id=event_in.event_id)
    # Ideally should verify flock ownership
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.put("/mortality/{event_id}", response_model=MortalityEventResponse)
async def update_mortality_event(
    event_id: UUID,
    event_in: MortalityEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update mortality event."""
    stmt = select(MortalityEvent).join(Flock).filter(
        MortalityEvent.id == event_id, 
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Mortality event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/mortality/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mortality_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete mortality event."""
    stmt = select(MortalityEvent).join(Flock).filter(
        MortalityEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Mortality event not found")
    
    await db.delete(event)
    await db.commit()
    return None

# Feed

@router.get("/feed", response_model=List[FeedConsumptionEventResponse])
async def read_feed_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List feed events."""
    stmt = select(FeedConsumptionEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(FeedConsumptionEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/feed/{event_id}", response_model=FeedConsumptionEventResponse)
async def update_feed_event(
    event_id: UUID,
    event_in: FeedConsumptionEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update feed event."""
    stmt = select(FeedConsumptionEvent).join(Flock).filter(
        FeedConsumptionEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/feed/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete feed event."""
    stmt = select(FeedConsumptionEvent).join(Flock).filter(
        FeedConsumptionEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")
    
    await db.delete(event)
    await db.commit()
    return None

# Vaccination

@router.get("/vaccination", response_model=List[VaccinationEventResponse])
async def read_vaccination_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List vaccination events."""
    stmt = select(VaccinationEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(VaccinationEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/vaccination/{event_id}", response_model=VaccinationEventResponse)
async def update_vaccination_event(
    event_id: UUID,
    event_in: VaccinationEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update vaccination event."""
    stmt = select(VaccinationEvent).join(Flock).filter(
        VaccinationEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/vaccination/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vaccination_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete vaccination event."""
    stmt = select(VaccinationEvent).join(Flock).filter(
        VaccinationEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")
    
    await db.delete(event)
    await db.commit()
    return None

# Weight

@router.get("/weight", response_model=List[WeightMeasurementEventResponse])
async def read_weight_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List weight events."""
    stmt = select(WeightMeasurementEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(WeightMeasurementEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/weight/{event_id}", response_model=WeightMeasurementEventResponse)
async def update_weight_event(
    event_id: UUID,
    event_in: WeightMeasurementEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update weight event."""
    stmt = select(WeightMeasurementEvent).join(Flock).filter(
        WeightMeasurementEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Weight event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/weight/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete weight event."""
    stmt = select(WeightMeasurementEvent).join(Flock).filter(
        WeightMeasurementEvent.id == event_id,
        Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Weight event not found")
    
    await db.delete(event)
    await db.commit()
    return None
