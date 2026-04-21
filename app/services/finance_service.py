from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.finance import Expenditure
from app.db.models.inventory import InventoryItem

# Standardized categories for the Kenyan broiler market (Starter Plan)
STARTER_EXPENSE_CATEGORIES: List[str] = [
    "feed",
    "chicks",
    "medicine",
    "vaccines",
    "charcoal",
    "sawdust",
    "water",
    "transport",
    "labor",
    "other",
]


class FinanceService:
    """Service for managing expenditures and sales with inventory integration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_expenditure(
        self,
        farmer_id: UUID,
        data: Dict,
        create_inventory_item: bool = False,
        new_inventory_name: Optional[str] = None,
        new_inventory_unit: Optional[str] = None,
    ) -> Expenditure:
        """Record a new expense, optionally linking to or creating an inventory item."""
        
        inventory_item_id = data.get("inventory_item_id")
        
        if create_inventory_item and new_inventory_name:
            # Create new inventory item
            new_inv = InventoryItem(
                farmer_id=farmer_id,
                name=new_inventory_name,
                category=data.get("category", "other"),
                unit=new_inventory_unit or data.get("unit", "pcs"),
                quantity=Decimal(str(data.get("quantity", 0))),
                cost_per_unit=Decimal(str(data.get("amount", 0))) / Decimal(str(data.get("quantity", 1))) if data.get("quantity") else 0,
                last_restocked=data.get("date"),
            )
            self.db.add(new_inv)
            await self.db.flush()
            inventory_item_id = new_inv.id

        expenditure = Expenditure(
            farmer_id=farmer_id,
            flock_id=data.get("flock_id"),
            date=data.get("date"),
            category=data.get("category"),
            description=data.get("description"),
            amount=Decimal(str(data.get("amount"))),
            quantity=Decimal(str(data.get("quantity"))) if data.get("quantity") else None,
            unit=data.get("unit"),
            mpesa_transaction_id=data.get("mpesa_transaction_id"),
            inventory_item_id=inventory_item_id,
            supplier_id=data.get("supplier_id"),
        )
        
        self.db.add(expenditure)
        await self.db.commit()
        await self.db.refresh(expenditure)
        return expenditure

    async def update_expenditure(
        self,
        expenditure: Expenditure,
        update_data: Dict,
        create_inventory_item: bool = False,
        new_inventory_name: Optional[str] = None,
        new_inventory_unit: Optional[str] = None,
        farmer_id: Optional[UUID] = None,
    ) -> Expenditure:
        """Update an existing expense."""
        
        if create_inventory_item and new_inventory_name and farmer_id:
            new_inv = InventoryItem(
                farmer_id=farmer_id,
                name=new_inventory_name,
                category=update_data.get("category") or expenditure.category,
                unit=new_inventory_unit or update_data.get("unit") or expenditure.unit or "pcs",
                quantity=Decimal(str(update_data.get("quantity", 0))),
                last_restocked=update_data.get("date") or expenditure.date,
            )
            self.db.add(new_inv)
            await self.db.flush()
            update_data["inventory_item_id"] = new_inv.id

        for field, value in update_data.items():
            if hasattr(expenditure, field):
                if field in ["amount", "quantity"] and value is not None:
                    setattr(expenditure, field, Decimal(str(value)))
                else:
                    setattr(expenditure, field, value)

        await self.db.commit()
        await self.db.refresh(expenditure)
        return expenditure

    async def sync_expenditure(
        self,
        farmer_id: UUID,
        amount: Decimal,
        category: str,
        description: str,
        date,
        flock_id: Optional[UUID] = None,
        related_id: Optional[UUID] = None,
        related_type: Optional[str] = None,
    ) -> Optional[Expenditure]:
        """Create or update an expenditure record linked to an event."""
        if amount is None or amount <= 0:
            if related_id and related_type:
                await self.delete_linked_expenditure(related_id, related_type)
            return None

        # Check if an expenditure already exists for this related object
        existing_exp = None
        if related_id and related_type:
            stmt = select(Expenditure).filter(
                and_(
                    Expenditure.related_id == related_id,
                    Expenditure.related_type == related_type,
                )
            )
            result = await self.db.execute(stmt)
            existing_exp = result.scalars().first()

        if existing_exp:
            existing_exp.amount = amount
            existing_exp.category = category
            existing_exp.description = description
            existing_exp.date = date
            existing_exp.flock_id = flock_id
            await self.db.commit()
            return existing_exp
        else:
            new_exp = Expenditure(
                farmer_id=farmer_id,
                flock_id=flock_id,
                amount=amount,
                category=category,
                description=description,
                date=date,
                related_id=related_id,
                related_type=related_type,
            )
            self.db.add(new_exp)
            await self.db.commit()
            return new_exp

    async def delete_linked_expenditure(self, related_id: UUID, related_type: str):
        """Delete an expenditure linked to a specific event."""
        stmt = select(Expenditure).filter(
            and_(
                Expenditure.related_id == related_id,
                Expenditure.related_type == related_type,
            )
        )
        result = await self.db.execute(stmt)
        existing_exp = result.scalars().first()
        if existing_exp:
            await self.db.delete(existing_exp)
            await self.db.commit()
