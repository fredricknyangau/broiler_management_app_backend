from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.base import Base

T = TypeVar('T', bound=Base)


class BaseEventService(Generic[T]):
    """
    Base service for all event types.
    Handles common operations: idempotency, CRUD, querying.
    """

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def create_event(self, event_data: dict) -> T:
        """
        Create an event with idempotency check.
        Returns existing event if event_id already exists.
        """
        event_id = event_data.get("event_id")
        
        # Check for existing event (idempotency)
        existing = self.get_by_event_id(event_id)
        if existing:
            return existing

        # Create new event
        try:
            event = self.model(**event_data)
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            return event
        except IntegrityError as e:
            self.db.rollback()
            # Race condition: another request created it
            existing = self.get_by_event_id(event_id)
            if existing:
                return existing
            raise e

    def get_by_id(self, event_id: UUID) -> Optional[T]:
        """Get event by primary key"""
        return self.db.query(self.model).filter(self.model.id == event_id).first()

    def get_by_event_id(self, event_id: UUID) -> Optional[T]:
        """Get event by idempotency key"""
        return self.db.query(self.model).filter(self.model.event_id == event_id).first()

    def get_by_flock(
        self, 
        flock_id: UUID, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[T]:
        """Get events for a specific flock with optional date range"""
        query = self.db.query(self.model).filter(self.model.flock_id == flock_id)
        
        if start_date:
            query = query.filter(self.model.event_date >= start_date)
        if end_date:
            query = query.filter(self.model.event_date <= end_date)
        
        return query.order_by(self.model.event_date.desc()).limit(limit).all()

    def delete_event(self, event_id: UUID) -> bool:
        """Delete an event by ID"""
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        self.db.delete(event)
        self.db.commit()
        return True

    def count_by_flock(self, flock_id: UUID) -> int:
        """Count total events for a flock"""
        return self.db.query(self.model).filter(self.model.flock_id == flock_id).count()

