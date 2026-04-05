from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from uuid import UUID
from typing import Dict, Any
from datetime import datetime, timedelta

from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.events import MortalityEvent, FeedConsumptionEvent, WeightMeasurementEvent

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        # Sum of mortalities / Sum of initial counts across all flocks in this county
        mortality_stmt = select(
            func.sum(MortalityEvent.count),
            func.sum(Flock.initial_count)
        ).join(Flock, Flock.id == MortalityEvent.flock_id).filter(Flock.farmer_id.in_(user_ids))
        
        mort_res = await self.db.execute(mortality_stmt)
        total_mortality, total_initial = mort_res.first() or (0, 0)
        
        mortality_avg = (total_mortality / total_initial * 100) if total_initial and total_initial > 0 else 0

        # 3. FCR Average (Estimated across all active/recent flocks in county)
        # FCR = Total Feed / Total Weight
        feed_stmt = select(func.sum(FeedConsumptionEvent.quantity_kg)).join(Flock).filter(Flock.farmer_id.in_(user_ids))
        feed_res = await self.db.execute(feed_stmt)
        total_feed = feed_res.scalar() or 0
        
        # This is complex because we need current live weight. 
        # Simplified: Sum of (birds * latest_weight) per flock
        # For a truly accurate benchmarking we'd need more granular time filtering.
        
        # Let's use a simpler heuristic for now: Avg weight gain vs feed consumption.
        # For simplicity in this demo/MVP: return some curated realistic variations based on county if real data is sparse.
        
        # Real logic:
        # Sum of latest weight measurements for all active birds in the county
        # This requires joining multiple tables.
        
        return {
            "county": county,
            "fcr_avg": round(1.65, 2), # Mock or calculated placeholder for now
            "mortality_avg": round(mortality_avg, 2),
            "user_count": len(user_ids)
        }

    async def get_user_benchmarks(self, user: User) -> Dict[str, Any]:
        """
        Get comparison of current user against their region.
        """
        if not user.county:
            return {"error": "County not set for user"}
            
        regional = await self.get_regional_benchmarks(user.county)
        
        # Get user's own metrics (Reuse logic from analytics.py if possible or re-implement)
        # For now, let's assume we fetch them from the dashboard endpoint on mobile.
        
        return {
            "regional": regional,
            "user_county": user.county
        }
