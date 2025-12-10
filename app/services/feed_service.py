from uuid import UUID
from datetime import date
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.db.models.events import FeedConsumptionEvent
from app.services.base_event_service import BaseEventService


class FeedConsumptionService(BaseEventService[FeedConsumptionEvent]):
    """Service for feed consumption operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(FeedConsumptionEvent, db)

    async def get_total_feed_consumed(
        self, 
        flock_id: UUID,
        feed_type: Optional[str] = None
    ) -> float:
        """Calculate total feed consumed (in kg)"""
        stmt = select(func.sum(FeedConsumptionEvent.quantity_kg)).filter(
            FeedConsumptionEvent.flock_id == flock_id
        )
        
        if feed_type:
            stmt = stmt.filter(FeedConsumptionEvent.feed_type == feed_type)
        
        result = await self.db.execute(stmt)
        return float(result.scalar() or 0)

    async def get_total_feed_cost(self, flock_id: UUID) -> float:
        """Calculate total feed cost (in KSh)"""
        result = await self.db.execute(
            select(func.sum(FeedConsumptionEvent.cost_ksh)).filter(
                FeedConsumptionEvent.flock_id == flock_id
            )
        )
        return float(result.scalar() or 0)

    async def get_feed_consumption_by_type(self, flock_id: UUID) -> Dict[str, float]:
        """Get feed consumption grouped by type"""
        result = await self.db.execute(
            select(
                FeedConsumptionEvent.feed_type,
                func.sum(FeedConsumptionEvent.quantity_kg).label('total_kg')
            ).filter(
                FeedConsumptionEvent.flock_id == flock_id
            ).group_by(
                FeedConsumptionEvent.feed_type
            )
        )
        results = result.all()
        
        return {feed_type or "Unknown": float(total) for feed_type, total in results}

    async def get_average_daily_consumption(self, flock_id: UUID, days: int) -> float:
        """Calculate average daily feed consumption"""
        total = await self.get_total_feed_consumed(flock_id)
        return round(total / days, 2) if days > 0 else 0

