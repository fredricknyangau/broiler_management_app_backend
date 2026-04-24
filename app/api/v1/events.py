from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (get_current_non_viewer, get_current_user, get_db)
from app.db.models.events import (FeedConsumptionEvent, MortalityEvent,
                                  VaccinationEvent, WeightMeasurementEvent)
from app.db.models.flock import Flock
from app.db.models.user import User
from app.schemas.daily_check import (FeedConsumptionEventCreate,
                                     FeedConsumptionEventResponse,
                                     FeedConsumptionEventUpdate,
                                     MortalityEventCreate,
                                     MortalityEventResponse,
                                     MortalityEventUpdate,
                                     VaccinationEventCreate,
                                     VaccinationEventResponse,
                                     VaccinationEventUpdate,
                                     WeightMeasurementEventCreate,
                                     WeightMeasurementEventResponse,
                                     WeightMeasurementEventUpdate)
from app.services.finance_service import FinanceService

router = APIRouter()


@router.get("/mortality", response_model=List[MortalityEventResponse])
async def read_mortality_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List mortality events."""
    stmt = select(MortalityEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(MortalityEvent.flock_id == flock_id)

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post(
    "/mortality",
    response_model=MortalityEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mortality_event(
    event_in: MortalityEventCreate,
    flock_id: UUID,  # Required query param
    event_date: date = None,  # Optional query param
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Create mortality event."""
    # Verify flock ownership
    stmt = select(Flock).filter(
        Flock.id == flock_id, Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    flock = result.scalars().first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")

    if event_date is None:
        event_date = date.today()

    event = MortalityEvent(
        **event_in.model_dump(exclude={"event_id"}),
        id=event_in.event_id,
        event_id=event_in.event_id,
        flock_id=flock_id,
        event_date=event_date,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/mortality/{event_id}", response_model=MortalityEventResponse)
async def update_mortality_event(
    event_id: UUID,
    event_in: MortalityEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update mortality event."""
    stmt = (
        select(MortalityEvent)
        .join(Flock)
        .filter(MortalityEvent.id == event_id, Flock.farmer_id == current_user.id)
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
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete mortality event."""
    stmt = (
        select(MortalityEvent)
        .join(Flock)
        .filter(MortalityEvent.id == event_id, Flock.farmer_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
):
    """List feed events."""
    stmt = (
        select(FeedConsumptionEvent)
        .join(Flock)
        .filter(Flock.farmer_id == current_user.id)
    )
    if flock_id:
        stmt = stmt.filter(FeedConsumptionEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post(
    "/feed",
    response_model=FeedConsumptionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feed_event(
    event_in: FeedConsumptionEventCreate,
    flock_id: UUID,
    event_date: date = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Create feed event."""
    # Verify flock ownership
    stmt = select(Flock).filter(
        Flock.id == flock_id, Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    flock = result.scalars().first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")

    if event_date is None:
        event_date = date.today()

    event = FeedConsumptionEvent(
        **event_in.model_dump(exclude={"event_id"}),
        id=event_in.event_id,
        event_id=event_in.event_id,
        flock_id=flock_id,
        event_date=event_date,
    )
    db.add(event)

    # Sync Expenditure
    if event.cost_ksh and event.cost_ksh > 0:
        finance_service = FinanceService(db)
        await finance_service.sync_expenditure(
            farmer_id=current_user.id,
            amount=event.cost_ksh,
            category="feed",
            description=f"Feed: {event.feed_type} for flock {flock.name}",
            date=event.event_date,
            flock_id=flock_id,
            related_id=event.id,
            related_type="feed",
        )
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/feed/{event_id}", response_model=FeedConsumptionEventResponse)
async def update_feed_event(
    event_id: UUID,
    event_in: FeedConsumptionEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update feed event."""
    stmt = (
        select(FeedConsumptionEvent)
        .join(Flock)
        .filter(FeedConsumptionEvent.id == event_id, Flock.farmer_id == current_user.id)
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")

    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    # Sync Expenditure
    finance_service = FinanceService(db)
    if event.cost_ksh and event.cost_ksh > 0:
        await finance_service.sync_expenditure(
            farmer_id=current_user.id,
            amount=event.cost_ksh,
            category="feed",
            description=f"Feed: {event.feed_type} for flock {event.flock.name}",
            date=event.event_date,
            flock_id=event.flock_id,
            related_id=event.id,
            related_type="feed",
        )
    else:
        # If cost was removed, delete linked expenditure
        await finance_service.delete_linked_expenditure(event.id, "feed")

    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/feed/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete feed event."""
    stmt = (
        select(FeedConsumptionEvent)
        .join(Flock)
        .filter(FeedConsumptionEvent.id == event_id, Flock.farmer_id == current_user.id)
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")

    # Delete linked expenditure first
    finance_service = FinanceService(db)
    await finance_service.delete_linked_expenditure(event.id, "feed")

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
    current_user: User = Depends(get_current_user),
):
    """List vaccination events."""
    stmt = (
        select(VaccinationEvent).join(Flock).filter(Flock.farmer_id == current_user.id)
    )
    if flock_id:
        stmt = stmt.filter(VaccinationEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post(
    "/vaccination",
    response_model=VaccinationEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vaccination_event(
    event_in: VaccinationEventCreate,
    flock_id: UUID,
    event_date: date = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Create vaccination event."""
    # Verify flock ownership
    stmt = select(Flock).filter(
        Flock.id == flock_id, Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    flock = result.scalars().first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")

    if event_date is None:
        event_date = date.today()

    event = VaccinationEvent(
        **event_in.model_dump(exclude={"event_id"}),
        id=event_in.event_id,
        event_id=event_in.event_id,
        flock_id=flock_id,
        event_date=event_date,
    )
    db.add(event)

    # Sync Expenditure
    if event.cost_ksh and event.cost_ksh > 0:
        finance_service = FinanceService(db)
        await finance_service.sync_expenditure(
            farmer_id=current_user.id,
            amount=event.cost_ksh,
            category="medicine",
            description=f"Vaccination: {event.vaccine_name} for flock {flock.name}",
            date=event.event_date,
            flock_id=flock_id,
            related_id=event.id,
            related_type="vaccination",
        )
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/vaccination/{event_id}", response_model=VaccinationEventResponse)
async def update_vaccination_event(
    event_id: UUID,
    event_in: VaccinationEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update vaccination event."""
    stmt = (
        select(VaccinationEvent)
        .join(Flock)
        .filter(VaccinationEvent.id == event_id, Flock.farmer_id == current_user.id)
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")

    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    # Sync Expenditure
    finance_service = FinanceService(db)
    if event.cost_ksh and event.cost_ksh > 0:
        await finance_service.sync_expenditure(
            farmer_id=current_user.id,
            amount=event.cost_ksh,
            category="medicine",
            description=f"Vaccination: {event.vaccine_name} for flock {event.flock.name}",
            date=event.event_date,
            flock_id=event.flock_id,
            related_id=event.id,
            related_type="vaccination",
        )
    else:
        await finance_service.delete_linked_expenditure(event.id, "vaccination")

    # db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/vaccination/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vaccination_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete vaccination event."""
    stmt = (
        select(VaccinationEvent)
        .join(Flock)
        .filter(VaccinationEvent.id == event_id, Flock.farmer_id == current_user.id)
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")

    # Delete linked expenditure first
    finance_service = FinanceService(db)
    await finance_service.delete_linked_expenditure(event.id, "vaccination")

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
    current_user: User = Depends(get_current_user),
):
    """List weight events."""
    stmt = (
        select(WeightMeasurementEvent)
        .join(Flock)
        .filter(Flock.farmer_id == current_user.id)
    )
    if flock_id:
        stmt = stmt.filter(WeightMeasurementEvent.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post(
    "/weight",
    response_model=WeightMeasurementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_weight_event(
    event_in: WeightMeasurementEventCreate,
    flock_id: UUID,
    event_date: date = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Create weight event."""
    # Verify flock ownership
    stmt = select(Flock).filter(
        Flock.id == flock_id, Flock.farmer_id == current_user.id
    )
    result = await db.execute(stmt)
    flock = result.scalars().first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")

    if event_date is None:
        event_date = date.today()

    event = WeightMeasurementEvent(
        **event_in.model_dump(exclude={"event_id"}),
        id=event_in.event_id,
        event_id=event_in.event_id,
        flock_id=flock_id,
        event_date=event_date,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/weight/{event_id}", response_model=WeightMeasurementEventResponse)
async def update_weight_event(
    event_id: UUID,
    event_in: WeightMeasurementEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update weight event."""
    stmt = (
        select(WeightMeasurementEvent)
        .join(Flock)
        .filter(
            WeightMeasurementEvent.id == event_id, Flock.farmer_id == current_user.id
        )
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
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete weight event."""
    stmt = (
        select(WeightMeasurementEvent)
        .join(Flock)
        .filter(
            WeightMeasurementEvent.id == event_id, Flock.farmer_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail="Weight event not found")

    await db.delete(event)
    await db.commit()
    return None
