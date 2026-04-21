"""
FinanceService — business logic layer for expenditures and sales.

Routers are thin HTTP adapters; all domain logic lives here.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.finance import Expenditure, Sale
from app.db.models.inventory import InventoryItem
from app.db.models.inventory_history import InventoryAction, InventoryHistory

# ── Whitelisted expense categories for the Starter plan ──────────────────────
STARTER_EXPENSE_CATEGORIES: frozenset[str] = frozenset(
    ["feed", "chicks", "medicine", "utilities", "other"]
)


class FinanceService:
    """Encapsulates all write business logic for the finance domain."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Expenditures ──────────────────────────────────────────────────────────

    async def create_expenditure(
        self,
        farmer_id: UUID,
        data: dict[str, Any],
        *,
        create_inventory_item: bool = False,
        new_inventory_name: str | None = None,
        new_inventory_unit: str | None = None,
    ) -> Expenditure:
        """
        Create an expenditure record and optionally link/update inventory.

        Logic:
          - If ``create_inventory_item`` is True and ``new_inventory_name`` is set,
            a new InventoryItem is created and linked.
          - If ``inventory_item_id`` is set in ``data``, the existing item's stock
            and cost_per_unit are updated.
          - An InventoryHistory entry is written for every stock movement.
        """
        expense_data = {
            k: v
            for k, v in data.items()
            if k
            not in ("create_inventory_item", "new_inventory_name", "new_inventory_unit")
        }

        inventory_id: UUID | None = data.get("inventory_item_id")

        if create_inventory_item and new_inventory_name:
            inventory_id = await self._create_and_link_inventory(
                farmer_id=farmer_id,
                name=new_inventory_name,
                unit=new_inventory_unit or data.get("unit") or "units",
                category=data.get("category", "other"),
                quantity=data.get("quantity") or 0,
                amount=data.get("amount", 0),
                expense_date=data.get("date"),
                description=data.get("description", ""),
            )
        elif inventory_id:
            await self._restock_inventory(
                inventory_id=inventory_id,
                quantity=data.get("quantity"),
                amount=data.get("amount"),
                expense_date=data.get("date"),
                description=data.get("description", ""),
                farmer_id=farmer_id,
            )

        item = Expenditure(**expense_data, farmer_id=farmer_id)
        item.inventory_item_id = inventory_id
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_expenditure(
        self,
        expenditure: Expenditure,
        update_data: dict[str, Any],
        *,
        create_inventory_item: bool = False,
        new_inventory_name: str | None = None,
        new_inventory_unit: str | None = None,
        farmer_id: UUID,
    ) -> Expenditure:
        """Update an expenditure, optionally creating a new linked inventory item."""
        # Strip special fields before setattr loop
        for special in (
            "create_inventory_item",
            "new_inventory_name",
            "new_inventory_unit",
        ):
            update_data.pop(special, None)

        if create_inventory_item and new_inventory_name:
            new_inv_id = await self._create_and_link_inventory(
                farmer_id=farmer_id,
                name=new_inventory_name,
                unit=new_inventory_unit or update_data.get("unit") or "units",
                category=update_data.get("category", "other"),
                quantity=update_data.get("quantity") or 0,
                amount=update_data.get("amount", 0),
                expense_date=update_data.get("date") or expenditure.date,
                description=update_data.get("description") or expenditure.description,
            )
            expenditure.inventory_item_id = new_inv_id

        for field, value in update_data.items():
            setattr(expenditure, field, value)

        await self.db.commit()
        await self.db.refresh(expenditure)
        return expenditure

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _create_and_link_inventory(
        self,
        *,
        farmer_id: UUID,
        name: str,
        unit: str,
        category: str,
        quantity: float,
        amount: float,
        expense_date: date | None,
        description: str,
    ) -> UUID:
        """Create a new InventoryItem and an initial PURCHASE history record."""
        # Map expense category → inventory category where sensible
        inv_category = (
            category if category in ("feed", "medicine", "equipment") else "other"
        )
        cost_per_unit = (amount / quantity) if quantity else 0.0

        new_item = InventoryItem(
            farmer_id=farmer_id,
            name=name,
            category=inv_category,
            quantity=quantity,
            unit=unit,
            cost_per_unit=cost_per_unit,
        )
        self.db.add(new_item)
        await self.db.flush()  # obtain PK before writing history

        if quantity > 0:
            history = InventoryHistory(
                inventory_item_id=new_item.id,
                user_id=farmer_id,
                date=expense_date,
                action=InventoryAction.PURCHASE,
                quantity_change=quantity,
                notes=f"Created via Expense: {description}",
            )
            self.db.add(history)

        return new_item.id

    async def _restock_inventory(
        self,
        *,
        inventory_id: UUID,
        quantity: float | None,
        amount: float | None,
        expense_date: date | None,
        description: str,
        farmer_id: UUID,
    ) -> None:
        """Add stock to an existing InventoryItem and update cost_per_unit."""
        result = await self.db.execute(
            select(InventoryItem).filter(InventoryItem.id == inventory_id)
        )
        inv_item = result.scalars().first()
        if not inv_item:
            return

        if quantity:
            inv_item.quantity += quantity
            history = InventoryHistory(
                inventory_item_id=inv_item.id,
                user_id=farmer_id,
                date=expense_date,
                action=InventoryAction.PURCHASE,
                quantity_change=quantity,
                notes=f"Expense: {description}",
            )
            self.db.add(history)

            # Weighted-average cost_per_unit update
            if amount:
                inv_item.cost_per_unit = amount / quantity

        inv_item.last_restocked = expense_date
