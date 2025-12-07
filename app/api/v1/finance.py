from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.finance import Expenditure, Sale
from app.db.models.user import User
from app.schemas.finance import (
    ExpenditureCreate, ExpenditureResponse, ExpenditureUpdate,
    SaleCreate, SaleResponse, SaleUpdate
)

router = APIRouter()

# --- Expendituers ---

@router.post("/expenditures", response_model=ExpenditureResponse, status_code=status.HTTP_201_CREATED)
def create_expenditure(
    item_in: ExpenditureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new expense.
    """
    item = Expenditure(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/expenditures", response_model=List[ExpenditureResponse])
def read_expenditures(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List expenditures, optionally filtered by flock_id.
    """
    query = db.query(Expenditure).filter(Expenditure.farmer_id == current_user.id)
    if flock_id:
        query = query.filter(Expenditure.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.put("/expenditures/{item_id}", response_model=ExpenditureResponse)
def update_expenditure(
    item_id: UUID,
    item_in: ExpenditureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an expense.
    """
    item = db.query(Expenditure).filter(Expenditure.id == item_id, Expenditure.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/expenditures/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expenditure(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an expenditure.
    """
    item = db.query(Expenditure).filter(Expenditure.id == item_id, Expenditure.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    
    db.delete(item)
    db.commit()
    return None

# --- Sales ---

@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    item_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new sale.
    """
    item = Sale(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/sales", response_model=List[SaleResponse])
def read_sales(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List sales, optionally filtered by flock_id.
    """
    query = db.query(Sale).filter(Sale.farmer_id == current_user.id)
    if flock_id:
        query = query.filter(Sale.flock_id == flock_id)
    return query.offset(skip).limit(limit).all()

@router.put("/sales/{item_id}", response_model=SaleResponse)
def update_sale(
    item_id: UUID,
    item_in: SaleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a sale record.
    """
    item = db.query(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/sales/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a sale record.
    """
    item = db.query(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")
    
    db.delete(item)
    db.commit()
    return None
