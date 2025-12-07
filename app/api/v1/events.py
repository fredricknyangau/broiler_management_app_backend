from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
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
def read_mortality_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List mortality events."""
    query = db.query(MortalityEvent).join(MortalityEvent.flock).filter(MortalityEvent.flock.has(farmer_id=current_user.id))
    if flock_id:
        query = query.filter(MortalityEvent.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.post("/mortality", response_model=MortalityEventResponse, status_code=status.HTTP_201_CREATED)
def create_mortality_event(
    event_in: MortalityEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create mortality event."""
    # Note: Logic usually goes through DailyCheckService, but standalone endpoint is ok
    event = MortalityEvent(**event_in.model_dump(exclude={"event_id"}), id=event_in.event_id)
    # Ideally should verify flock ownership
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.put("/mortality/{event_id}", response_model=MortalityEventResponse)
def update_mortality_event(
    event_id: UUID,
    event_in: MortalityEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update mortality event."""
    event = db.query(MortalityEvent).join(MortalityEvent.flock).filter(
        MortalityEvent.id == event_id, 
        MortalityEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Mortality event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.delete("/mortality/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mortality_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete mortality event."""
    event = db.query(MortalityEvent).join(MortalityEvent.flock).filter(
        MortalityEvent.id == event_id,
        MortalityEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Mortality event not found")
    
    db.delete(event)
    db.commit()
    return None

# Feed

@router.get("/feed", response_model=List[FeedConsumptionEventResponse])
def read_feed_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List feed events."""
    query = db.query(FeedConsumptionEvent).join(FeedConsumptionEvent.flock).filter(FeedConsumptionEvent.flock.has(farmer_id=current_user.id))
    if flock_id:
        query = query.filter(FeedConsumptionEvent.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.put("/feed/{event_id}", response_model=FeedConsumptionEventResponse)
def update_feed_event(
    event_id: UUID,
    event_in: FeedConsumptionEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update feed event."""
    event = db.query(FeedConsumptionEvent).join(FeedConsumptionEvent.flock).filter(
        FeedConsumptionEvent.id == event_id,
        FeedConsumptionEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.delete("/feed/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feed_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete feed event."""
    event = db.query(FeedConsumptionEvent).join(FeedConsumptionEvent.flock).filter(
        FeedConsumptionEvent.id == event_id,
        FeedConsumptionEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Feed event not found")
    
    db.delete(event)
    db.commit()
    return None

# Vaccination

@router.get("/vaccination", response_model=List[VaccinationEventResponse])
def read_vaccination_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List vaccination events."""
    query = db.query(VaccinationEvent).join(VaccinationEvent.flock).filter(VaccinationEvent.flock.has(farmer_id=current_user.id))
    if flock_id:
        query = query.filter(VaccinationEvent.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.put("/vaccination/{event_id}", response_model=VaccinationEventResponse)
def update_vaccination_event(
    event_id: UUID,
    event_in: VaccinationEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update vaccination event."""
    event = db.query(VaccinationEvent).join(VaccinationEvent.flock).filter(
        VaccinationEvent.id == event_id,
        VaccinationEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.delete("/vaccination/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vaccination_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete vaccination event."""
    event = db.query(VaccinationEvent).join(VaccinationEvent.flock).filter(
        VaccinationEvent.id == event_id,
        VaccinationEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Vaccination event not found")
    
    db.delete(event)
    db.commit()
    return None

# Weight

@router.get("/weight", response_model=List[WeightMeasurementEventResponse])
def read_weight_events(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List weight events."""
    query = db.query(WeightMeasurementEvent).join(WeightMeasurementEvent.flock).filter(WeightMeasurementEvent.flock.has(farmer_id=current_user.id))
    if flock_id:
        query = query.filter(WeightMeasurementEvent.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.put("/weight/{event_id}", response_model=WeightMeasurementEventResponse)
def update_weight_event(
    event_id: UUID,
    event_in: WeightMeasurementEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update weight event."""
    event = db.query(WeightMeasurementEvent).join(WeightMeasurementEvent.flock).filter(
        WeightMeasurementEvent.id == event_id,
        WeightMeasurementEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Weight event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.delete("/weight/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete weight event."""
    event = db.query(WeightMeasurementEvent).join(WeightMeasurementEvent.flock).filter(
        WeightMeasurementEvent.id == event_id,
        WeightMeasurementEvent.flock.has(farmer_id=current_user.id)
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Weight event not found")
    
    db.delete(event)
    db.commit()
    return None
