from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import Dict, Any, List
from datetime import date, timedelta
import csv
import io

from app.api.deps import get_db, get_current_user, set_tenant_context
from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.finance import Sale, Expenditure
from app.db.models.events import MortalityEvent, FeedConsumptionEvent, WeightMeasurementEvent
from app.db.models.inventory import InventoryItem
from app.db.models.biosecurity import BiosecurityCheck
from app.db.models.subscription import Subscription, SubscriptionStatus, PlanType

router = APIRouter()

@router.get("/dashboard-metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get aggregated performance metrics for the user's farm.
    """
    # Active Flocks
    active_flocks_result = await db.execute(
        select(func.count(Flock.id)).filter(
            Flock.id != None, # Dummy true
            Flock.farmer_id == current_user.id,
            Flock.status == "active"
        )
    )
    active_flocks_count = active_flocks_result.scalar() or 0

    # Active Flocks List
    active_flocks_result = await db.execute(
        select(Flock).filter(
            Flock.farmer_id == current_user.id,
            Flock.status == "active"
        )
    )
    active_flocks = active_flocks_result.scalars().all()
    
    # Calculate current birds for active flocks and FCR
    total_current_birds = 0
    total_feed = 0
    total_live_weight_kg = 0

    for flock in active_flocks:
         mortality_res = await db.execute(select(func.sum(MortalityEvent.count)).filter(MortalityEvent.flock_id == flock.id))
         mortality = mortality_res.scalar() or 0
         
         sold_res = await db.execute(select(func.sum(Sale.quantity)).filter(Sale.flock_id == flock.id))
         sold = sold_res.scalar() or 0
         
         current_birds = flock.initial_count - mortality - sold
         total_current_birds += current_birds

         # Feed Consumed
         feed_res = await db.execute(select(func.sum(FeedConsumptionEvent.quantity_kg)).filter(FeedConsumptionEvent.flock_id == flock.id))
         feed = feed_res.scalar() or 0
         total_feed += float(feed) if feed else 0

         # Latest Weight
         weight_res = await db.execute(
             select(WeightMeasurementEvent.average_weight_grams)
             .filter(WeightMeasurementEvent.flock_id == flock.id)
             .order_by(WeightMeasurementEvent.measurement_date.desc())
             .limit(1)
         )
         avg_weight_g = weight_res.scalar() or 0
         avg_weight_kg = float(avg_weight_g) / 1000.0 if avg_weight_g else 0
         total_live_weight_kg += (current_birds * avg_weight_kg)

    fcr_rate = 0
    if total_live_weight_kg > 0:
        fcr_rate = total_feed / total_live_weight_kg

    # Financials
    total_revenue_res = await db.execute(select(func.sum(Sale.total_amount)).filter(Sale.farmer_id == current_user.id))
    total_revenue = total_revenue_res.scalar() or 0
    
    total_expenses_res = await db.execute(select(func.sum(Expenditure.amount)).filter(Expenditure.farmer_id == current_user.id))
    total_expenses = total_expenses_res.scalar() or 0
    
    net_profit = total_revenue - total_expenses

    # Mortality Rate (Global)
    all_active_flocks_initial_birds_res = await db.execute(
        select(func.sum(Flock.initial_count)).filter(
            Flock.farmer_id == current_user.id
        )
        # Assuming we want mortality rate over *all time* or just active?
        # The original code filtered active flocks implicitly via logic or maybe not.
        # Original: db.query(func.sum(Flock.initial_count)).filter(Flock.farmer_id == current_user.id)
        # So it takes all flocks.
    )
    all_flocks_initial_birds = all_active_flocks_initial_birds_res.scalar() or 0
    
    all_mortality_res = await db.execute(
        select(func.sum(MortalityEvent.count))
        .join(Flock)
        .filter(Flock.farmer_id == current_user.id)
    )
    all_mortality = all_mortality_res.scalar() or 0
    
    mortality_rate = 0
    if all_flocks_initial_birds > 0:
        mortality_rate = (all_mortality / all_flocks_initial_birds) * 100

    activities = []
    
    # 1. Recent Sales
    sales_res = await db.execute(
        select(Sale).filter(Sale.farmer_id == current_user.id).order_by(Sale.date.desc()).limit(2)
    )
    for s in sales_res.scalars().all():
        activities.append({
            "title": "Sale Recorded",
            "desc": f"Sold {s.quantity} birds",
            "date": s.date.isoformat(),
            "type": "sale"
        })
        
    # 2. Recent Expenditures
    expenses_res = await db.execute(
        select(Expenditure).filter(Expenditure.farmer_id == current_user.id).order_by(Expenditure.date.desc()).limit(2)
    )
    for e in expenses_res.scalars().all():
        activities.append({
            "title": "Expense Recorded",
            "desc": f"{e.category}: KES {e.amount}",
            "date": e.date.isoformat(),
            "type": "expense"
        })
        
    # 3. Recent Mortalities
    _mort_res = await db.execute(
        select(MortalityEvent).join(Flock).filter(Flock.farmer_id == current_user.id).order_by(MortalityEvent.event_date.desc()).limit(2)
    )
    for m in _mort_res.scalars().all():
        activities.append({
            "title": "Mortality Recorded",
            "desc": f"{m.count} birds lost",
            "date": m.event_date.isoformat(),
            "type": "mortality"
        })
        
    # 4. Recent Feeds
    _feed_res = await db.execute(
        select(FeedConsumptionEvent).join(Flock).filter(Flock.farmer_id == current_user.id).order_by(FeedConsumptionEvent.event_date.desc()).limit(2)
    )
    for f in _feed_res.scalars().all():
        activities.append({
            "title": "Feed Recorded",
            "desc": f"{f.feed_type.title()}: {f.quantity_kg}kg",
            "date": f.event_date.isoformat(),
            "type": "feed"
        })

    activities.sort(key=lambda x: x['date'], reverse=True)

    return {
        "active_flocks": active_flocks_count,
        "current_birds": max(0, total_current_birds),
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expenses),
        "net_profit": float(net_profit),
        "mortality_rate": float(round(mortality_rate, 2)),
        "fcr_rate": float(round(fcr_rate, 2)),
        "recent_activities": activities[:5]
    }

@router.get("/charts/revenue-vs-expenses")
async def get_revenue_expenses_chart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get monthly revenue vs expenses for the last 6 months.
    """
    # Enforce Plan Limits for Advanced Analytics
    sub_res = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.created_at.desc())
    )
    sub = sub_res.scalars().first()
    current_plan = sub.plan_type if sub else PlanType.STARTER

    if current_plan == PlanType.STARTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced Financial Analytics requires a Professional Plan subscription."
        )
    today = date.today()
    start_date = today - timedelta(days=180)
    
    sales_res = await db.execute(
        select(Sale).filter(
            Sale.farmer_id == current_user.id,
            Sale.date >= start_date
        )
    )
    sales = sales_res.scalars().all()
    
    expenses_res = await db.execute(
        select(Expenditure).filter(
            Expenditure.farmer_id == current_user.id,
            Expenditure.date >= start_date
        )
    )
    expenses = expenses_res.scalars().all()
    
    # Aggregate data by Month (YYYY-MM)
    monthly_data = {}
    
    # Initialize last 6 months
    for i in range(6):
        d = today - timedelta(days=i*30)
        key = d.strftime("%Y-%m")
        monthly_data[key] = {"name": d.strftime("%b"), "revenue": 0, "expenses": 0}

    for s in sales:
        key = s.date.strftime("%Y-%m")
        if key in monthly_data:
            monthly_data[key]["revenue"] += float(s.total_amount)
            
    for e in expenses:
        key = e.date.strftime("%Y-%m")
        if key in monthly_data:
            monthly_data[key]["expenses"] += float(e.amount)
            
    # Sort and return list
    sorted_keys = sorted(monthly_data.keys())
    return [monthly_data[k] for k in sorted_keys]


@router.get("/reports/export")
async def export_report(
    report_type: str = Query(..., regex="^(financial|inventory|production)$"),
    format: str = Query("csv", regex="^csv$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export data as CSV.
    """
    # Enforce Plan Limits for Reports Export
    sub_res = await db.execute(
        select(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.created_at.desc())
    )
    sub = sub_res.scalars().first()
    current_plan = sub.plan_type if sub else PlanType.STARTER

    if current_plan == PlanType.STARTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Exporting reports requires a Professional Plan subscription."
        )
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "financial":
        writer.writerow(["Date", "Type", "Category/Item", "Amount", "Description"])
        
        # Sales
        sales_res = await db.execute(select(Sale).filter(Sale.farmer_id == current_user.id))
        sales = sales_res.scalars().all()
        for s in sales:
            writer.writerow([s.date, "Income", "Chicken Sales", s.total_amount, s.notes or ""])
            
        # Expenses
        expenses_res = await db.execute(select(Expenditure).filter(Expenditure.farmer_id == current_user.id))
        expenses = expenses_res.scalars().all()
        for e in expenses:
            writer.writerow([e.date, "Expense", e.category, e.amount, e.description])

    elif report_type == "inventory":
        writer.writerow(["Item Name", "Category", "Quantity", "Unit", "Cost Per Unit"])
        items_res = await db.execute(select(InventoryItem).filter(InventoryItem.farmer_id == current_user.id))
        items = items_res.scalars().all()
        for i in items:
            writer.writerow([i.name, i.category, i.quantity, i.unit, i.cost_per_unit])

    elif report_type == "production":
        writer.writerow(["Flock Name", "Start Date", "Initial Chicks", "Current Status"])
        flocks_res = await db.execute(select(Flock).filter(Flock.farmer_id == current_user.id))
        flocks = flocks_res.scalars().all()
        for f in flocks:
            writer.writerow([f.name, f.start_date, f.initial_count, f.status])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"}
    )

