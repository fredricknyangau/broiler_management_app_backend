import csv
import io
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (get_current_user, get_db, get_plan_type)
from app.db.models.finance import Expenditure, Sale
from app.db.models.flock import Flock
from app.db.models.inventory import InventoryItem
from app.db.models.subscription import PlanType
from app.db.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/benchmarks")
async def get_benchmarks(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get regional benchmarks for the current user's county.
    """
    if not current_user.county:
        return {
            "county": None,
            "fcr_avg": 0,
            "mortality_avg": 0,
            "user_count": 0,
            "message": "Update your profile with a County to see benchmarks.",
        }

    service = AnalyticsService(db)
    result = await service.get_regional_benchmarks(current_user.county)
    return result


@router.get("/dashboard-metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get aggregated performance metrics for the user's farm.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_metrics(current_user)


@router.get("/charts/revenue-vs-expenses")
async def get_revenue_expenses_chart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_plan: str = Depends(get_plan_type),
) -> List[Dict[str, Any]]:
    """
    Get monthly revenue vs expenses for the last 6 months.
    """
    if current_plan == PlanType.STARTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced Financial Analytics requires a Professional Plan subscription.",
        )

    service = AnalyticsService(db)
    return await service.get_revenue_expenses_chart(current_user.id)


@router.get("/reports/export")
async def export_report(
    report_type: str = Query(..., pattern="^(financial|inventory|production)$"),
    file_format: str = Query("csv", pattern="^csv$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_plan: str = Depends(get_plan_type),
):
    """
    Export data as CSV. Requires Professional Plan.
    """
    if current_plan == PlanType.STARTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Exporting reports requires a Professional Plan subscription.",
        )
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "financial":
        writer.writerow(["Date", "Type", "Category/Item", "Amount", "Description"])

        # Sales
        sales_res = await db.execute(
            select(Sale).filter(Sale.farmer_id == current_user.id)
        )
        sales = sales_res.scalars().all()
        for s in sales:
            writer.writerow(
                [s.date, "Income", "Chicken Sales", s.total_amount, s.notes or ""]
            )

        # Expenses
        expenses_res = await db.execute(
            select(Expenditure).filter(Expenditure.farmer_id == current_user.id)
        )
        expenses = expenses_res.scalars().all()
        for e in expenses:
            writer.writerow([e.date, "Expense", e.category, e.amount, e.description])

    elif report_type == "inventory":
        writer.writerow(["Item Name", "Category", "Quantity", "Unit", "Cost Per Unit"])
        items_res = await db.execute(
            select(InventoryItem).filter(InventoryItem.farmer_id == current_user.id)
        )
        items = items_res.scalars().all()
        for i in items:
            writer.writerow([i.name, i.category, i.quantity, i.unit, i.cost_per_unit])

    elif report_type == "production":
        writer.writerow(
            ["Flock Name", "Start Date", "Initial Chicks", "Current Status"]
        )
        flocks_res = await db.execute(
            select(Flock).filter(Flock.farmer_id == current_user.id)
        )
        flocks = flocks_res.scalars().all()
        for f in flocks:
            writer.writerow([f.name, f.start_date, f.initial_count, f.status])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={report_type}_report.csv"
        },
    )
