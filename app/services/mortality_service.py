from uuid import UUID
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.db.models.events import MortalityEvent
from app.services.base_event_service import BaseEventService


class MortalityEventService(BaseEventService[MortalityEvent]):
    """Service for mortality event operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(MortalityEvent, db)

    async def get_total_mortality(self, flock_id: UUID) -> int:
        """Calculate total mortality count for a flock"""
        result = await self.db.execute(
            select(func.sum(MortalityEvent.count)).filter(
                MortalityEvent.flock_id == flock_id
            )
        )
        return result.scalar() or 0

    async def get_mortality_rate(self, flock_id: UUID, initial_count: int) -> float:
        """Calculate mortality rate as percentage"""
        total_deaths = await self.get_total_mortality(flock_id)
        if initial_count == 0:
            return 0.0
        return round((total_deaths / initial_count) * 100, 2)

    async def get_weekly_mortality(
        self, 
        flock_id: UUID, 
        week_start: date
    ) -> int:
        """Get mortality count for a specific week"""
        week_end = week_start + timedelta(days=6)
        events = await self.get_by_flock(flock_id, start_date=week_start, end_date=week_end)
        return sum(event.count for event in events)

    async def get_mortality_by_cause(self, flock_id: UUID) -> dict:
        """Get mortality counts grouped by cause"""
        result = await self.db.execute(
            select(
                MortalityEvent.cause,
                func.sum(MortalityEvent.count).label('total')
            ).filter(
                MortalityEvent.flock_id == flock_id
            ).group_by(
                MortalityEvent.cause
            )
        )
        results = result.all()
        
        return {cause or "Unknown": int(total) for cause, total in results}

