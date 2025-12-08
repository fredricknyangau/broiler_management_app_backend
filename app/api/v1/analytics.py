from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import date, timedelta

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.finance import Sale, Expenditure
from app.db.models.events import MortalityEvent, FeedConsumptionEvent

router = APIRouter()

@router.get("/dashboard-metrics")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get aggregated performance metrics for the user's farm.
    """
    # Active Flocks
    active_flocks_count = db.query(Flock).filter(
        Flock.farmer_id == current_user.id,
        Flock.status == "active"
    ).count()

    # Total Birds (Initial count of all active flocks)
    # Note: This is simplified. Real current birds = initial - mortality - sales
    active_flocks = db.query(Flock).filter(
        Flock.farmer_id == current_user.id,
        Flock.status == "active"
    ).all()
    
    total_birds_initial = sum(f.initial_count for f in active_flocks)
    
    # Calculate current birds for active flocks
    total_current_birds = 0
    for flock in active_flocks:
         mortality = db.query(func.sum(MortalityEvent.count)).filter(MortalityEvent.flock_id == flock.id).scalar() or 0
         sold = db.query(func.sum(Sale.quantity)).filter(Sale.flock_id == flock.id).scalar() or 0
         total_current_birds += (flock.initial_count - mortality - sold)

    # Financials
    total_revenue = db.query(func.sum(Sale.total_amount)).filter(Sale.farmer_id == current_user.id).scalar() or 0
    total_expenses = db.query(func.sum(Expenditure.amount)).filter(Expenditure.farmer_id == current_user.id).scalar() or 0
    net_profit = total_revenue - total_expenses

    # Mortality Rate (Global)
    # Ensure denominator is not zero
    all_flocks_initial_birds = db.query(func.sum(Flock.initial_count)).filter(Flock.farmer_id == current_user.id).scalar() or 0
    all_mortality = db.query(func.sum(MortalityEvent.count)).join(Flock).filter(Flock.farmer_id == current_user.id).scalar() or 0
    
    mortality_rate = 0
    if all_flocks_initial_birds > 0:
        mortality_rate = (all_mortality / all_flocks_initial_birds) * 100

    return {
        "active_flocks": active_flocks_count,
        "current_birds": max(0, total_current_birds),
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expenses),
        "net_profit": float(net_profit),
        "mortality_rate": float(round(mortality_rate, 2))
    }

@router.get("/charts/revenue-vs-expenses")
def get_revenue_expenses_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get monthly revenue vs expenses for the last 6 months.
    """
    today = date.today()
    start_date = today - timedelta(days=180)
    
    # We ideally group by month. Postgres specific: date_trunc('month', date)
    # For DB agnostic: fetch all in range and aggregate in python (easier for prototype)
    
    sales = db.query(Sale).filter(
        Sale.farmer_id == current_user.id,
        Sale.date >= start_date
    ).all()
    
    expenses = db.query(Expenditure).filter(
        Expenditure.farmer_id == current_user.id,
        Expenditure.date >= start_date
    ).all()
    
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
    result = sorted(monthly_data.values(), key=lambda x: x['name']) # Sort by month name is flawed if crossing years? 
    # Use keys to sort
    sorted_keys = sorted(monthly_data.keys())
    return [monthly_data[k] for k in sorted_keys]

