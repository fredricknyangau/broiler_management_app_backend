from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.inventory import InventoryItem
from app.db.models.user import User
from app.schemas.inventory import InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate

router = APIRouter()

@router.post("/", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    item_in: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new item to inventory.
    """
    item = InventoryItem(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/", response_model=List[InventoryItemResponse])
def read_inventory_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List inventory items.
    """
    return db.query(InventoryItem).filter(InventoryItem.farmer_id == current_user.id).offset(skip).limit(limit).all()

@router.put("/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: UUID,
    item_in: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update stock levels or details.
    """
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    # Check for Low Stock Alert
    if item.quantity <= item.minimum_stock:
        from app.services.alert_service import AlertService
        from app.db.models.flock import Flock
        
        # Find an active flock to attach alert to (Alerts currently require a flock_id)
        # TODO: Refactor Alert model to make flock_id optional for system-wide alerts
        active_flock = db.query(Flock).filter(
            Flock.farmer_id == current_user.id, 
            Flock.status == 'active'
        ).first()
        
        if active_flock:
            service = AlertService(db)
            service.create_alert(
                flock_id=active_flock.id,
                title="Low Inventory Stock",
                message=f"Stock for '{item.name}' is low ({item.quantity} {item.unit}). Reorder level: {item.minimum_stock}.",
                severity="high",
                alert_type="inventory"
            )
            
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an inventory item.
    """
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.farmer_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return None
