from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.base import Base

T = TypeVar('T', bound=Base)


class BaseEventService(Generic[T]):
    """
    Base service for all event types.
    Handles common operations: idempotency, CRUD, querying.
    """

    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def create_event(self, event_data: dict) -> T:
        """
        Create an event with idempotency check.
        Returns existing event if event_id already exists.
        """
        event_id = event_data.get("event_id")
        
        # Check for existing event (idempotency)
        existing = await self.get_by_event_id(event_id)
        if existing:
            return existing

        # Create new event
        try:
            event = self.model(**event_data)
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except IntegrityError as e:
            await self.db.rollback()
            # Race condition: another request created it
            existing = await self.get_by_event_id(event_id)
            if existing:
                return existing
            raise e

    async def get_by_id(self, event_id: UUID) -> Optional[T]:
        """Get event by primary key"""
        result = await self.db.execute(select(self.model).filter(self.model.id == event_id))
        return result.scalars().first()

    async def get_by_event_id(self, event_id: UUID) -> Optional[T]:
        """Get event by idempotency key"""
        result = await self.db.execute(select(self.model).filter(self.model.event_id == event_id))
        return result.scalars().first()

    async def get_by_flock(
        self, 
        flock_id: UUID, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[T]:
        """Get events for a specific flock with optional date range"""
        stmt = select(self.model).filter(self.model.flock_id == flock_id)
        
        if start_date:
            stmt = stmt.filter(self.model.event_date >= start_date)
        if end_date:
            stmt = stmt.filter(self.model.event_date <= end_date)
        
        stmt = stmt.order_by(self.model.event_date.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_event(self, event_id: UUID) -> bool:
        """Delete an event by ID"""
        event = await self.get_by_id(event_id)
        if not event:
            return False
        
        await self.db.delete(event)
        await self.db.commit()
        return True

    async def count_by_flock(self, flock_id: UUID) -> int:
        """Count total events for a flock"""
        # Optimized count? For now, list len or simple query
        # Correct way in 2.0: select(func.count()).select_from(Model)...
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(self.model).filter(self.model.flock_id == flock_id)
        )
        return result.scalar_one()


