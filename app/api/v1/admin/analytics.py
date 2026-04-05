"""admin/analytics.py — System and financial analytics for the admin dashboard."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.api.deps import get_db, get_current_admin_user
from app.db.models.user import User
from app.db.models.finance import Sale, Expenditure
from app.db.models.flock import Flock
from app.db.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan

router = APIRouter()


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    active_subscriptions: int
    total_revenue_est: float
    total_flocks: int
    active_flocks: int = 0
    users_growth_percent: float = 0.0
    revenue_growth_percent: float = 0.0
    users_by_plan: Dict[str, int] = {}
    mrr: float = 0.0


class AggregateAnalytics(BaseModel):
    date: str
    total_revenue: float = 0.0
    total_expenses: float = 0.0
    total_birds: int = 0


@router.get("/stats", response_model=AdminStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get system-wide statistics including billing."""
    total_users = await db.execute(select(func.count(User.id)))
    active_users = await db.execute(select(func.count(User.id)).filter(User.is_active == True))

    total_flocks = await db.execute(select(func.count(Flock.id)))
    active_flocks = await db.execute(select(func.count(Flock.id)).filter(Flock.status == "active"))

    active_subs_result = await db.execute(
        select(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    active_subs = active_subs_result.scalars().all()
    active_subs_count = len(active_subs)

    users_by_plan = {}
    revenue = 0.0
    mrr = 0.0
    price_map = {}
    plans_res = await db.execute(select(SubscriptionPlan))
    for p in plans_res.scalars().all():
        try:
            price_map[p.plan_type] = float(p.monthly_price)
        except:
            price_map[p.plan_type] = 0.0

    for sub in active_subs:
        try:
            if getattr(sub, "amount", None):
                revenue += float(sub.amount)
        except:
            pass
        plan = str(sub.plan_type).upper()
        users_by_plan[plan] = users_by_plan.get(plan, 0) + 1
        mrr += price_map.get(plan, 0.0)

    # Calculate M-o-M Growth
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    users_tm_res = await db.execute(
        select(func.count(User.id)).filter(User.created_at >= thirty_days_ago)
    )
    users_lm_res = await db.execute(
        select(func.count(User.id)).filter(
            User.created_at >= sixty_days_ago, User.created_at < thirty_days_ago
        )
    )
    users_tm = users_tm_res.scalar() or 0
    users_lm = users_lm_res.scalar() or 0
    users_growth = ((users_tm - users_lm) / users_lm * 100.0) if users_lm > 0 else (100.0 if users_tm > 0 else 0.0)

    rev_tm_res = await db.execute(
        select(Subscription).filter(
            Subscription.created_at >= thirty_days_ago, Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    rev_lm_res = await db.execute(
        select(Subscription).filter(
            Subscription.created_at >= sixty_days_ago,
            Subscription.created_at < thirty_days_ago,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )

    def sum_rev(subs):
        return sum(float(s.amount) for s in subs if s.amount and s.amount.replace(".", "", 1).isdigit())

    rev_tm = sum_rev(rev_tm_res.scalars().all())
    rev_lm = sum_rev(rev_lm_res.scalars().all())
    rev_growth = ((rev_tm - rev_lm) / rev_lm * 100.0) if rev_lm > 0 else (100.0 if rev_tm > 0 else 0.0)

    return AdminStats(
        total_users=total_users.scalar() or 0,
        active_users=active_users.scalar() or 0,
        active_subscriptions=active_subs_count,
        total_revenue_est=revenue,
        total_flocks=total_flocks.scalar() or 0,
        active_flocks=active_flocks.scalar() or 0,
        users_growth_percent=round(users_growth, 2),
        revenue_growth_percent=round(rev_growth, 2),
        users_by_plan=users_by_plan,
        mrr=mrr,
    )


@router.get("/analytics/aggregate", response_model=List[AggregateAnalytics])
async def get_aggregate_analytics(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get system-wide aggregate financial and flock metrics grouped by date (last 6 months)."""
    today = datetime.now().date()
    start_date = today - timedelta(days=180)

    sales_stmt = (
        select(Sale.date, func.coalesce(func.sum(Sale.total_amount), 0).label("amount"))
        .filter(Sale.date >= start_date)
        .group_by(Sale.date)
    )
    sales_res = await db.execute(sales_stmt)
    sales = {r.date: r.amount for r in sales_res.all()}

    expenses_stmt = (
        select(Expenditure.date, func.coalesce(func.sum(Expenditure.amount), 0).label("amount"))
        .filter(Expenditure.date >= start_date)
        .group_by(Expenditure.date)
    )
    expenses_res = await db.execute(expenses_stmt)
    expenses = {r.date: r.amount for r in expenses_res.all()}

    flocks_stmt = (
        select(Flock.start_date, func.coalesce(func.sum(Flock.initial_count), 0).label("birds"))
        .filter(Flock.start_date >= start_date)
        .group_by(Flock.start_date)
    )
    flocks_res = await db.execute(flocks_stmt)
    flocks = {r.start_date: r.birds for r in flocks_res.all()}

    all_dates = sorted(set(list(sales.keys()) + list(expenses.keys()) + list(flocks.keys())))
    result = []
    for d in all_dates:
        result.append(
            AggregateAnalytics(
                date=d.strftime("%Y-%m-%d"),
                total_revenue=float(sales.get(d, 0)),
                total_expenses=float(expenses.get(d, 0)),
                total_birds=int(flocks.get(d, 0)),
            )
        )

    return result
