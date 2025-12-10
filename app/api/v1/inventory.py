from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from datetime import date

from app.api.deps import get_db, get_current_user
from app.db.models.inventory import InventoryItem
from app.db.models.user import User
from app.db.models.inventory_history import InventoryHistory, InventoryAction
from app.schemas.inventory import InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate, InventoryHistoryResponse
from app.services.alert_service import AlertService

router = APIRouter()

@router.post("/", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    item_in: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new item to inventory.
    """
    item = InventoryItem(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    await db.flush() # Get ID
    
    # Log History
    if item.quantity > 0:
        history = InventoryHistory(
            inventory_item_id=item.id,
            user_id=current_user.id,
            date=date.today(),
            action=InventoryAction.PURCHASE if item.cost_per_unit > 0 else InventoryAction.ADJUSTMENT,
            quantity_change=item.quantity,
            notes="Initial stock"
        )
        db.add(history)
        
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/", response_model=List[InventoryItemResponse])
async def read_inventory_items(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List inventory items.
    """
    result = await db.execute(
        select(InventoryItem)
        .filter(InventoryItem.farmer_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.put("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: UUID,
    item_in: InventoryItemUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update stock levels or details.
    """
    result = await db.execute(select(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Calculate difference for history
    old_qty = item.quantity
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    new_qty = item.quantity
    diff = new_qty - old_qty
    
    if diff != 0:
        history = InventoryHistory(
            inventory_item_id=item.id,
            user_id=current_user.id,
            date=item.last_restocked or date.today(),
            action=InventoryAction.RESTOCK if diff > 0 else InventoryAction.ADJUSTMENT,
            quantity_change=diff,
            notes=item_in.notes or "Manual adjustment"
        )
        db.add(history)

    await db.commit()
    await db.refresh(item)
    
    # Check for Low Stock Alert using Service
    alert_service = AlertService(db)
    await alert_service.check_low_stock(
        item_name=item.name,
        current_qty=float(item.quantity),
        min_qty=float(item.minimum_stock),
        background_tasks=background_tasks,
        flock_id=None # Global alert
    )
            
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an inventory item.
    """
    result = await db.execute(select(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return None

@router.get("/{item_id}/history", response_model=List[InventoryHistoryResponse])
async def read_inventory_history(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get history for a specific inventory item.
    """
    result = await db.execute(
        select(InventoryHistory)
        .filter(InventoryHistory.inventory_item_id == item_id)
        .order_by(InventoryHistory.created_at.desc())
    )
    return result.scalars().all()
