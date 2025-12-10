from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from datetime import date

from app.api.deps import get_db, get_current_user
from app.db.models.finance import Expenditure, Sale
from app.db.models.user import User
from app.db.models.inventory import InventoryItem
from app.schemas.finance import (
    ExpenditureCreate, ExpenditureResponse, ExpenditureUpdate,
    SaleCreate, SaleResponse, SaleUpdate
)
from app.db.models.inventory_history import InventoryHistory, InventoryAction
from app.services.alert_service import AlertService
from fastapi import BackgroundTasks

router = APIRouter()

# --- Expendituers ---

@router.post("/expenditures", response_model=ExpenditureResponse, status_code=status.HTTP_201_CREATED)
async def create_expenditure(
    item_in: ExpenditureCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new expense.
    """
    expense_data = item_in.model_dump(exclude={'create_inventory_item', 'new_inventory_name', 'new_inventory_unit'})
    
    # Handle Inventory Linking/Creation
    inventory_id = item_in.inventory_item_id
    
    if item_in.create_inventory_item and item_in.new_inventory_name:
        # Create new inventory item
        new_item = InventoryItem(
            farmer_id=current_user.id,
            name=item_in.new_inventory_name,
            category='other', # Default, maybe infer from expense category?
            quantity=item_in.quantity or 0,
            unit=item_in.new_inventory_unit or item_in.unit or 'units',
            cost_per_unit=item_in.amount / (item_in.quantity or 1) if item_in.quantity else 0
        )
        # Try to map category
        if item_in.category in ['feed', 'medicine', 'equipment']:
            new_item.category = item_in.category
            
        db.add(new_item)
        await db.flush() # Get ID
        inventory_id = new_item.id
        
        # Log History (New Item)
        if new_item.quantity > 0:
            history = InventoryHistory(
                inventory_item_id=new_item.id,
                user_id=current_user.id,
                date=item_in.date,
                action=InventoryAction.PURCHASE,
                quantity_change=new_item.quantity,
                notes=f"Created via Expense: {item_in.description}"
            )
            db.add(history)
    
    elif item_in.inventory_item_id:
        # Update existing inventory
        result = await db.execute(select(InventoryItem).filter(InventoryItem.id == item_in.inventory_item_id))
        inv_item = result.scalars().first()
        if inv_item:
            # Assuming buying adds to stock
            if item_in.quantity:
                inv_item.quantity += item_in.quantity
                
                # Log History (Restock)
                history = InventoryHistory(
                    inventory_item_id=inv_item.id,
                    user_id=current_user.id,
                    date=item_in.date,
                    action=InventoryAction.PURCHASE,
                    quantity_change=item_in.quantity,
                    notes=f"Expense: {item_in.description}"
                )
                db.add(history)

            # Update cost per unit potentially? weighted average? simple replacement?
            # Let's simple replace cost_per_unit if we have valid data
            if item_in.quantity and item_in.amount:
                 unique_cost = item_in.amount / item_in.quantity
                 inv_item.cost_per_unit = unique_cost
            inv_item.last_restocked = item_in.date

    item = Expenditure(**expense_data, farmer_id=current_user.id)
    item.inventory_item_id = inventory_id
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    # Check Low Stock (if linked)
    if inventory_id:
        # Re-fetch inventory item to get latest qty
        result = await db.execute(select(InventoryItem).filter(InventoryItem.id == inventory_id))
        inv_item = result.scalars().first()
        if inv_item:
            alert_service = AlertService(db)
            await alert_service.check_low_stock(
                item_name=inv_item.name,
                current_qty=float(inv_item.quantity),
                min_qty=float(inv_item.minimum_stock),
                background_tasks=background_tasks,
                flock_id=item.flock_id # Optional link
            )

    return item

@router.get("/expenditures", response_model=List[ExpenditureResponse])
async def read_expenditures(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List expenditures, optionally filtered by flock_id.
    """
    stmt = select(Expenditure).filter(Expenditure.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(Expenditure.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/expenditures/{item_id}", response_model=ExpenditureResponse)
async def update_expenditure(
    item_id: UUID,
    item_in: ExpenditureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an expense.
    """
    result = await db.execute(select(Expenditure).filter(Expenditure.id == item_id, Expenditure.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    
    # Handle Inventory Linkage during Update
    if item_in.create_inventory_item and item_in.new_inventory_name:
         # Create new inventory item
        new_item = InventoryItem(
            farmer_id=current_user.id,
            name=item_in.new_inventory_name,
            category='other', 
            quantity=item_in.quantity or 0,
            unit=item_in.new_inventory_unit or item_in.unit or 'units',
            cost_per_unit=item_in.amount / (item_in.quantity or 1) if item_in.quantity else 0
        )
        if item_in.category in ['feed', 'medicine', 'equipment']:
            new_item.category = item_in.category
            
        db.add(new_item)
        await db.flush()
        
        item.inventory_item_id = new_item.id
        
        # Log History
        if new_item.quantity > 0:
            history = InventoryHistory(
                inventory_item_id=new_item.id,
                user_id=current_user.id,
                date=item_in.date or item.date,
                action=InventoryAction.PURCHASE,
                quantity_change=new_item.quantity,
                notes=f"Created via Expense Update: {item_in.description or item.description}"
            )
            db.add(history)
            
    elif item_in.inventory_item_id:
        # Link to existing (Update logic is complex: assuming we ADD to it?)
        # For simplicity in update, we just link it. Stock adjustments on update are tricky 
        # (need to reverse old, apply new). For now, let's just Set the link.
        item.inventory_item_id = item_in.inventory_item_id

    # Exclude special fields
    update_data.pop('create_inventory_item', None)
    update_data.pop('new_inventory_name', None)
    update_data.pop('new_inventory_unit', None)

    for field, value in update_data.items():
        setattr(item, field, value)
    
    # db.add(item) # No need to add if it's an existing object being modified
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/expenditures/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expenditure(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an expenditure.
    """
    result = await db.execute(select(Expenditure).filter(Expenditure.id == item_id, Expenditure.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    
    await db.delete(item)
    await db.commit()
    return None

# --- Sales ---

@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    item_in: SaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a new sale.
    """
    item = Sale(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/sales", response_model=List[SaleResponse])
async def read_sales(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List sales, optionally filtered by flock_id.
    """
    stmt = select(Sale).filter(Sale.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(Sale.flock_id == flock_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/sales/{item_id}", response_model=SaleResponse)
async def update_sale(
    item_id: UUID,
    item_in: SaleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a sale record.
    """
    result = await db.execute(select(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    # db.add(item) # No need to add if it's an existing object being modified
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/sales/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a sale record.
    """
    result = await db.execute(select(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")
    
    await db.delete(item)
    await db.commit()
    return None
