from uuid import UUID
from datetime import date
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.events import FeedConsumptionEvent
from app.services.base_event_service import BaseEventService


class FeedConsumptionService(BaseEventService[FeedConsumptionEvent]):
    """Service for feed consumption operations"""

    def __init__(self, db: Session):
        super().__init__(FeedConsumptionEvent, db)

    def get_total_feed_consumed(
        self, 
        flock_id: UUID,
        feed_type: Optional[str] = None
    ) -> float:
        """Calculate total feed consumed (in kg)"""
        query = self.db.query(func.sum(FeedConsumptionEvent.quantity_kg)).filter(
            FeedConsumptionEvent.flock_id == flock_id
        )
        
        if feed_type:
            query = query.filter(FeedConsumptionEvent.feed_type == feed_type)
        
        result = query.scalar()
        return float(result or 0)

    def get_total_feed_cost(self, flock_id: UUID) -> float:
        """Calculate total feed cost (in KSh)"""
        result = self.db.query(func.sum(FeedConsumptionEvent.cost_ksh)).filter(
            FeedConsumptionEvent.flock_id == flock_id
        ).scalar()
        return float(result or 0)

    def get_feed_consumption_by_type(self, flock_id: UUID) -> Dict[str, float]:
        """Get feed consumption grouped by type"""
        results = self.db.query(
            FeedConsumptionEvent.feed_type,
            func.sum(FeedConsumptionEvent.quantity_kg).label('total_kg')
        ).filter(
            FeedConsumptionEvent.flock_id == flock_id
        ).group_by(
            FeedConsumptionEvent.feed_type
        ).all()
        
        return {feed_type or "Unknown": float(total) for feed_type, total in results}

    def get_average_daily_consumption(self, flock_id: UUID, days: int) -> float:
        """Calculate average daily feed consumption"""
        total = self.get_total_feed_consumed(flock_id)
        return round(total / days, 2) if days > 0 else 0

