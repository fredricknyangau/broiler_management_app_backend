from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.health import VetConsultation
from app.db.models.user import User
from app.schemas.health import VetConsultationCreate, VetConsultationResponse

router = APIRouter()

@router.post("/consultations", response_model=VetConsultationResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    item_in: VetConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new vet consultation.
    """
    item = VetConsultation(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/consultations", response_model=List[VetConsultationResponse])
def read_consultations(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List vet consultations.
    """
    query = db.query(VetConsultation).filter(VetConsultation.farmer_id == current_user.id)
    if flock_id:
        query = query.filter(VetConsultation.flock_id == flock_id)
    return query.order_by(VetConsultation.visit_date.desc()).offset(skip).limit(limit).all()

@router.put("/consultations/{consultation_id}", response_model=VetConsultationResponse)
def update_consultation(
    consultation_id: UUID,
    item_in: VetConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a vet consultation.
    """
    item = db.query(VetConsultation).filter(VetConsultation.id == consultation_id, VetConsultation.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
