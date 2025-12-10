from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.health import VetConsultation
from app.db.models.user import User
from app.schemas.health import VetConsultationCreate, VetConsultationResponse

router = APIRouter()

@router.post("/consultations", response_model=VetConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(
    item_in: VetConsultationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new vet consultation.
    """
    item = VetConsultation(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/consultations", response_model=List[VetConsultationResponse])
async def read_consultations(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List vet consultations.
    """
    stmt = select(VetConsultation).filter(VetConsultation.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(VetConsultation.flock_id == flock_id)
    result = await db.execute(stmt.order_by(VetConsultation.visit_date.desc()).offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/consultations/{consultation_id}", response_model=VetConsultationResponse)
async def update_consultation(
    consultation_id: UUID,
    item_in: VetConsultationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a vet consultation.
    """
    result = await db.execute(select(VetConsultation).filter(VetConsultation.id == consultation_id, VetConsultation.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    # db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
