from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, literal_column
from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime, date, timedelta

from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.finance import Sale, Expenditure
from app.db.models.events import MortalityEvent, FeedConsumptionEvent, WeightMeasurementEvent

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(self, current_user: User) -> Dict[str, Any]:
        """
        Calculates all dashboard metrics using bulk SQL queries instead of per-flock loops.
        """
        # 1. Fetch all active flocks for this user
        active_flocks_stmt = select(Flock).filter(
            Flock.farmer_id == current_user.id,
            Flock.status == "active"
        )
        active_flocks_res = await self.db.execute(active_flocks_stmt)
        active_flocks = active_flocks_res.scalars().all()
        flock_ids = [f.id for f in active_flocks]
        active_flocks_count = len(flock_ids)

        if not flock_ids:
            # Fallback for users with no active flocks, still want global stats
            return await self._get_empty_dashboard_fallback(current_user)

        # 2. Bulk Aggregates per flock
        # We fetch totals for all active flocks in single group-by passes
        
        mortality_stmt = select(
            MortalityEvent.flock_id, 
            func.sum(MortalityEvent.count).label("total")
        ).filter(MortalityEvent.flock_id.in_(flock_ids)).group_by(MortalityEvent.flock_id)
        
        sales_stmt = select(
            Sale.flock_id, 
            func.sum(Sale.quantity).label("total")
        ).filter(Sale.flock_id.in_(flock_ids)).group_by(Sale.flock_id)
        
        feed_stmt = select(
            FeedConsumptionEvent.flock_id, 
            func.sum(FeedConsumptionEvent.quantity_kg).label("total")
        ).filter(FeedConsumptionEvent.flock_id.in_(flock_ids)).group_by(FeedConsumptionEvent.flock_id)

        # Execute these in semi-parallel (awaited independently here for simplicity but better than N+1)
        mort_data = {r[0]: r[1] for r in (await self.db.execute(mortality_stmt)).all()}
        sale_data = {r[0]: r[1] for r in (await self.db.execute(sales_stmt)).all()}
        feed_data = {r[0]: r[1] for r in (await self.db.execute(feed_stmt)).all()}

        # 3. Latest Weight per Flock (The "Hard" Query)
        # We use a subquery to find the latest date per flock
        latest_weight_date_sub = select(
            WeightMeasurementEvent.flock_id,
            func.max(WeightMeasurementEvent.event_date).label("max_date")
        ).filter(WeightMeasurementEvent.flock_id.in_(flock_ids)).group_by(WeightMeasurementEvent.flock_id).subquery()

        # Join to get the weight for that date
        latest_weight_stmt = select(
            WeightMeasurementEvent.flock_id,
            WeightMeasurementEvent.average_weight_grams
        ).join(
            latest_weight_date_sub,
            and_(
                WeightMeasurementEvent.flock_id == latest_weight_date_sub.c.flock_id,
                WeightMeasurementEvent.event_date == latest_weight_date_sub.c.max_date
            )
        )
        weight_data = {r[0]: r[1] for r in (await self.db.execute(latest_weight_stmt)).all()}

        # 4. Integrate results
        total_current_birds = 0
        total_feed = 0
        total_live_weight_kg = 0

        for flock in active_flocks:
            morts = mort_data.get(flock.id, 0)
            sales = sale_data.get(flock.id, 0)
            feed = feed_data.get(flock.id, 0)
            weight_g = weight_data.get(flock.id, 0)

            current_birds = flock.initial_count - morts - sales
            total_current_birds += current_birds
            total_feed += float(feed)
            
            avg_weight_kg = float(weight_g) / 1000.0 if weight_g else 0
            total_live_weight_kg += (current_birds * avg_weight_kg)

        fcr_rate = total_feed / total_live_weight_kg if total_live_weight_kg > 0 else 0

        # 5. Global Stats
        total_revenue_res = await self.db.execute(select(func.sum(Sale.total_amount)).filter(Sale.farmer_id == current_user.id))
        total_expenses_res = await self.db.execute(select(func.sum(Expenditure.amount)).filter(Expenditure.farmer_id == current_user.id))
        
        # mortality global
        all_initial_res = await self.db.execute(select(func.sum(Flock.initial_count)).filter(Flock.farmer_id == current_user.id))
        all_mort_res = await self.db.execute(
            select(func.sum(MortalityEvent.count)).join(Flock).filter(Flock.farmer_id == current_user.id)
        )
        
        all_initial = all_initial_res.scalar() or 0
        all_mort = all_mort_res.scalar() or 0
        mortality_rate = (all_mort / all_initial * 100) if all_initial > 0 else 0

        return {
            "active_flocks": active_flocks_count,
            "current_birds": max(0, total_current_birds),
            "total_revenue": float(total_revenue_res.scalar() or 0),
            "total_expenses": float(total_expenses_res.scalar() or 0),
            "net_profit": float((total_revenue_res.scalar() or 0) - (total_expenses_res.scalar() or 0)),
            "mortality_rate": round(mortality_rate, 2),
            "fcr_rate": round(fcr_rate, 2),
            "recent_activities": await self._get_recent_activities(current_user.id)
        }

    async def _get_empty_dashboard_fallback(self, current_user: User) -> Dict[str, Any]:
        """Returns global metrics only when no active flocks exist."""
        # Simple implementation for fallback
        rev = (await self.db.execute(select(func.sum(Sale.total_amount)).filter(Sale.farmer_id == current_user.id))).scalar() or 0
        exp = (await self.db.execute(select(func.sum(Expenditure.amount)).filter(Expenditure.farmer_id == current_user.id))).scalar() or 0
        return {
            "active_flocks": 0,
            "current_birds": 0,
            "total_revenue": float(rev),
            "total_expenses": float(exp),
            "net_profit": float(rev - exp),
            "mortality_rate": 0,
            "fcr_rate": 0,
            "recent_activities": await self._get_recent_activities(current_user.id)
        }

    async def _get_recent_activities(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Consolidates latest events across all domains into a feed."""
        activities = []
        
        # Sales
        res = await self.db.execute(select(Sale).filter(Sale.farmer_id == user_id).order_by(desc(Sale.date)).limit(2))
        for s in res.scalars().all():
            activities.append({"title": "Sale Recorded", "desc": f"Sold {s.quantity} birds", "date": s.date.isoformat(), "type": "sale"})
            
        # Expenses
        res = await self.db.execute(select(Expenditure).filter(Expenditure.farmer_id == user_id).order_by(desc(Expenditure.date)).limit(2))
        for e in res.scalars().all():
            activities.append({"title": "Expense Recorded", "desc": f"{e.category}: KES {e.amount}", "date": e.date.isoformat(), "type": "expense"})
            
        # Mortalities
        res = await self.db.execute(select(MortalityEvent).join(Flock).filter(Flock.farmer_id == user_id).order_by(desc(MortalityEvent.event_date)).limit(2))
        for m in res.scalars().all():
            activities.append({"title": "Mortality Recorded", "desc": f"{m.count} birds lost", "date": m.event_date.isoformat(), "type": "mortality"})
            
        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:5]

    async def get_regional_benchmarks(self, county: str) -> Dict[str, Any]:
        """
        Calculate anonymized regional averages for FCR and Mortality.
        """
        if not county:
            return {"fcr_avg": 0, "mortality_avg": 0, "sample_size": 0}

        # 1. Get all users in this county
        users_stmt = select(User.id).filter(User.county == county)
        user_ids_res = await self.db.execute(users_stmt)
        user_ids = [row[0] for row in user_ids_res.all()]
        
        if not user_ids:
            return {"fcr_avg": 0, "mortality_avg": 0, "sample_size": 0}

        # 2. Mortality Average
        mortality_stmt = select(
            func.sum(MortalityEvent.count),
            func.sum(Flock.initial_count)
        ).join(Flock, Flock.id == MortalityEvent.flock_id).filter(Flock.farmer_id.in_(user_ids))
        
        mort_res = await self.db.execute(mortality_stmt)
        total_mortality, total_initial = mort_res.first() or (0, 0)
        
        mortality_avg = (total_mortality / total_initial * 100) if total_initial and total_initial > 0 else 0

        # Placeholder for FCR Benchmarking in this region
        return {
            "county": county,
            "fcr_avg": 1.65, 
            "mortality_avg": round(mortality_avg, 2),
            "user_count": len(user_ids)
        }

    async def get_user_benchmarks(self, user: User) -> Dict[str, Any]:
        """
        Get comparison of current user against their region.
        """
        if not user.county:
            return {"message": "Update your profile with a County to see benchmarks."}
            
        regional = await self.get_regional_benchmarks(user.county)
        return {
            "regional": regional,
            "user_county": user.county
        }

    async def get_revenue_expenses_chart(self, user_id: UUID, days: int = 180) -> List[Dict[str, Any]]:
        """
        Fetches monthly aggregated revenue vs expenses using SQL date_trunc grouping.
        """
        start_date = date.today() - timedelta(days=days)
        
        # 1. Initialize map with last 6 months (zero-filled)
        today = date.today()
        monthly_data = {}
        for i in range(6):
            # Move back by months approximately
            d = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            key = d.strftime("%Y-%m")
            monthly_data[key] = {"name": d.strftime("%b"), "revenue": 0, "expenses": 0}

        # 2. Revenue Grouped Query
        # Using date_trunc('month', ...) for Postgres-native monthly grouping
        rev_stmt = select(
            func.date_trunc('month', Sale.date).label('month'),
            func.sum(Sale.total_amount).label('total')
        ).filter(
            Sale.farmer_id == user_id,
            Sale.date >= start_date
        ).group_by(literal_column('month'))
        
        rev_res = await self.db.execute(rev_stmt)
        for row in rev_res.all():
            if row[0]:
                key = row[0].strftime("%Y-%m")
                if key in monthly_data:
                    monthly_data[key]["revenue"] = float(row[1])

        # 3. Expenses Grouped Query
        exp_stmt = select(
            func.date_trunc('month', Expenditure.date).label('month'),
            func.sum(Expenditure.amount).label('total')
        ).filter(
            Expenditure.farmer_id == user_id,
            Expenditure.date >= start_date
        ).group_by(literal_column('month'))
        
        exp_res = await self.db.execute(exp_stmt)
        for row in exp_res.all():
            if row[0]:
                key = row[0].strftime("%Y-%m")
                if key in monthly_data:
                    monthly_data[key]["expenses"] = float(row[1])

        # 4. Return sorted by date
        return [monthly_data[k] for k in sorted(monthly_data.keys())]


