from uuid import UUID
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.events import MortalityEvent
from app.services.base_event_service import BaseEventService


class MortalityEventService(BaseEventService[MortalityEvent]):
    """Service for mortality event operations"""

    def __init__(self, db: Session):
        super().__init__(MortalityEvent, db)

    def get_total_mortality(self, flock_id: UUID) -> int:
        """Calculate total mortality count for a flock"""
        result = self.db.query(func.sum(MortalityEvent.count)).filter(
            MortalityEvent.flock_id == flock_id
        ).scalar()
        return result or 0

    def get_mortality_rate(self, flock_id: UUID, initial_count: int) -> float:
        """Calculate mortality rate as percentage"""
        total_deaths = self.get_total_mortality(flock_id)
        if initial_count == 0:
            return 0.0
        return round((total_deaths / initial_count) * 100, 2)

    def get_weekly_mortality(
        self, 
        flock_id: UUID, 
        week_start: date
    ) -> int:
        """Get mortality count for a specific week"""
        week_end = week_start + timedelta(days=6)
        events = self.get_by_flock(flock_id, start_date=week_start, end_date=week_end)
        return sum(event.count for event in events)

    def get_mortality_by_cause(self, flock_id: UUID) -> dict:
        """Get mortality counts grouped by cause"""
        results = self.db.query(
            MortalityEvent.cause,
            func.sum(MortalityEvent.count).label('total')
        ).filter(
            MortalityEvent.flock_id == flock_id
        ).group_by(
            MortalityEvent.cause
        ).all()
        
        return {cause or "Unknown": int(total) for cause, total in results}

