"""
Finance router — thin HTTP adapter for expenditures and sales.

All business logic lives in FinanceService.  Subscription plan enforcement uses
the shared ``get_plan_type`` dependency from ``deps.py`` — no inline duplicated
subscription lookups.
"""

import csv
import io
from datetime import date, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (check_professional_subscription,
                          get_current_non_viewer, get_current_user, get_db,
                          get_plan_type, set_tenant_context)
from app.db.models.finance import Expenditure, Sale
from app.db.models.inventory import InventoryItem
from app.db.models.subscription import PlanType
from app.db.models.user import User
from app.schemas.finance import (ExpenditureCreate, ExpenditureResponse,
                                 ExpenditureUpdate, SaleCreate, SaleResponse,
                                 SaleUpdate)
from app.services.alert_service import AlertService
from app.services.finance_service import (STARTER_EXPENSE_CATEGORIES,
                                          FinanceService)
from app.services.mpesa_service import mpesa_service

router = APIRouter()


# ─── Expenditures ────────────────────────────────────────────────────────────


@router.post(
    "/expenditures",
    response_model=ExpenditureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expenditure(
    item_in: ExpenditureCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
    current_plan: str = Depends(get_plan_type),
):
    """Record a new expense."""
    if (
        current_plan == PlanType.STARTER
        and item_in.category.lower() not in STARTER_EXPENSE_CATEGORIES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Custom expense categories require a Professional Plan. Allowed: {', '.join(STARTER_EXPENSE_CATEGORIES)}.",
        )

    service = FinanceService(db)
    item = await service.create_expenditure(
        farmer_id=current_user.id,
        data=item_in.model_dump(),
        create_inventory_item=item_in.create_inventory_item or False,
        new_inventory_name=item_in.new_inventory_name,
        new_inventory_unit=item_in.new_inventory_unit,
    )

    # Check Low Stock alert after linking to inventory
    if item.inventory_item_id:
        result = await db.execute(
            select(InventoryItem).filter(InventoryItem.id == item.inventory_item_id)
        )
        inv_item = result.scalars().first()
        if inv_item:
            alert_service = AlertService(db)
            await alert_service.check_low_stock(
                item_name=inv_item.name,
                current_qty=float(inv_item.quantity),
                min_qty=float(inv_item.minimum_stock),
                background_tasks=background_tasks,
                flock_id=item.flock_id,
            )

    return item


@router.get("/expenditures", response_model=List[ExpenditureResponse])
async def read_expenditures(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_plan: str = Depends(get_plan_type),
):
    """List expenditures, optionally filtered by flock_id."""
    stmt = select(Expenditure).filter(Expenditure.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(Expenditure.flock_id == flock_id)

    # Starter plan: restrict to last 90 days of history
    if current_plan == PlanType.STARTER:
        stmt = stmt.filter(Expenditure.date >= date.today() - timedelta(days=90))

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.put("/expenditures/{item_id}", response_model=ExpenditureResponse)
async def update_expenditure(
    item_id: UUID,
    item_in: ExpenditureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
    current_plan: str = Depends(get_plan_type),
):
    """Update an expense."""
    result = await db.execute(
        select(Expenditure).filter(
            Expenditure.id == item_id, Expenditure.farmer_id == current_user.id
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")

    if (
        item_in.category
        and current_plan == PlanType.STARTER
        and item_in.category.lower() not in STARTER_EXPENSE_CATEGORIES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Custom expense categories require a Professional Plan. Allowed: {', '.join(STARTER_EXPENSE_CATEGORIES)}.",
        )

    service = FinanceService(db)
    return await service.update_expenditure(
        expenditure=item,
        update_data=item_in.model_dump(exclude_unset=True),
        create_inventory_item=item_in.create_inventory_item or False,
        new_inventory_name=item_in.new_inventory_name,
        new_inventory_unit=item_in.new_inventory_unit,
        farmer_id=current_user.id,
    )


@router.delete("/expenditures/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expenditure(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete an expenditure."""
    result = await db.execute(
        select(Expenditure).filter(
            Expenditure.id == item_id, Expenditure.farmer_id == current_user.id
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Expenditure not found")
    await db.delete(item)
    await db.commit()


# ─── Sales ────────────────────────────────────────────────────────────────────


@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    item_in: SaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Record a new sale, optionally triggering an M-Pesa STK push to the buyer."""
    item = Sale(**item_in.model_dump(), farmer_id=current_user.id)
    db.add(item)
    await db.flush()  # obtain PK before initiating STK push

    if item_in.buyer_phone:
        try:
            response = await mpesa_service.initiate_stk_push(
                phone=item_in.buyer_phone,
                amount=int(float(item_in.total_amount)),
                reference=f"SALE-{item.id}",
            )
            item.checkout_request_id = response.get("CheckoutRequestID")
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to initiate M-Pesa push: {e}",
            )

    await db.commit()
    await db.refresh(item)
    return item


@router.get("/sales", response_model=List[SaleResponse])
async def read_sales(
    flock_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_plan: str = Depends(get_plan_type),
):
    """List sales, optionally filtered by flock_id."""
    stmt = select(Sale).filter(Sale.farmer_id == current_user.id)
    if flock_id:
        stmt = stmt.filter(Sale.flock_id == flock_id)

    if current_plan == PlanType.STARTER:
        stmt = stmt.filter(Sale.date >= date.today() - timedelta(days=90))

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.put("/sales/{item_id}", response_model=SaleResponse)
async def update_sale(
    item_id: UUID,
    item_in: SaleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Update a sale record."""
    result = await db.execute(
        select(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")

    for field, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/sales/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_non_viewer),
):
    """Delete a sale record."""
    result = await db.execute(
        select(Sale).filter(Sale.id == item_id, Sale.farmer_id == current_user.id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Sale record not found")
    await db.delete(item)
    await db.commit()


# ─── Export ──────────────────────────────────────────────────────────────────


@router.get("/export", dependencies=[Depends(check_professional_subscription)])
async def export_financials(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export financial data (Sales & Expenditures) as CSV.
    Requires Professional Plan.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category/Item", "Amount (KES)", "Description"])

    sales_res = await db.execute(select(Sale).filter(Sale.farmer_id == current_user.id))
    for s in sales_res.scalars().all():
        writer.writerow(
            [s.date, "Income", "Chicken Sales", float(s.total_amount), s.notes or ""]
        )

    expenses_res = await db.execute(
        select(Expenditure).filter(Expenditure.farmer_id == current_user.id)
    )
    for e in expenses_res.scalars().all():
        writer.writerow([e.date, "Expense", e.category, float(e.amount), e.description])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial_report.csv"},
    )
