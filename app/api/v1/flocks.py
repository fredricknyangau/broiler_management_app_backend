
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.flock import Flock
from app.db.models.user import User
from app.schemas.flock import FlockCreate, FlockResponse, FlockUpdate
from app.services.vaccination_service import VaccinationService

router = APIRouter()

@router.post("/", response_model=FlockResponse, status_code=status.HTTP_201_CREATED)
def create_flock(
    flock_in: FlockCreate,
    db: Session = Depends(get_db),
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
    db.add(flock)
    db.commit()
    db.refresh(flock)
    
    # Auto-generate vaccination schedule
    vaccination_service = VaccinationService(db)
    vaccination_service.generate_schedule(flock.id, flock.commencement_date)

    return flock

@router.get("/", response_model=List[FlockResponse])
def read_flocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all flocks owned by the current user.
    
    - **skip**: Pagination offset
    - **limit**: Max number of records to return
    """
    flocks = db.query(Flock).filter(Flock.farmer_id == current_user.id).offset(skip).limit(limit).all()
    return flocks

@router.get("/{flock_id}", response_model=FlockResponse)
def read_flock(
    flock_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific flock by ID.
    
    - Validates ownership (returns 404 if flock belongs to another user).
    """
    flock = db.query(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id).first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    return flock

@router.put("/{flock_id}", response_model=FlockResponse)
def update_flock(
    flock_id: UUID,
    flock_in: FlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a flock's details.
    
    - Only provided fields will be updated (partial update).
    """
    flock = db.query(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id).first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    
    update_data = flock_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flock, field, value)
    
    db.add(flock)
    db.commit()
    db.refresh(flock)
    return flock

@router.delete("/{flock_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flock(
    flock_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a flock.
    
    - Cascades delete to all related events (mortality, feed, etc.) due to DB constraints.
    """
    flock = db.query(Flock).filter(Flock.id == flock_id, Flock.farmer_id == current_user.id).first()
    if not flock:
        raise HTTPException(status_code=404, detail="Flock not found")
    
    db.delete(flock)
    db.commit()
    return None
