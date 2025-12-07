from uuid import UUID
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.models.events import VaccinationEvent
from app.services.base_event_service import BaseEventService


class VaccinationService(BaseEventService[VaccinationEvent]):
    """Service for vaccination event operations"""

    def __init__(self, db: Session):
        super().__init__(VaccinationEvent, db)

    def get_upcoming_vaccinations(
        self, 
        flock_id: UUID, 
        days_ahead: int = 7
    ) -> List[VaccinationEvent]:
        """Get vaccinations due in the next N days"""
        today = date.today()
        future_date = today + timedelta(days=days_ahead)
        
        return self.db.query(VaccinationEvent).filter(
            and_(
                VaccinationEvent.flock_id == flock_id,
                VaccinationEvent.next_due_date.isnot(None),
                VaccinationEvent.next_due_date >= today,
                VaccinationEvent.next_due_date <= future_date
            )
        ).order_by(VaccinationEvent.next_due_date).all()

    def get_overdue_vaccinations(self, flock_id: UUID) -> List[VaccinationEvent]:
        """Get vaccinations that are overdue"""
        today = date.today()
        
        return self.db.query(VaccinationEvent).filter(
            and_(
                VaccinationEvent.flock_id == flock_id,
                VaccinationEvent.next_due_date.isnot(None),
                VaccinationEvent.next_due_date < today
            )
        ).order_by(VaccinationEvent.next_due_date).all()

    def get_vaccination_history(
        self, 
        flock_id: UUID, 
        disease_target: Optional[str] = None
    ) -> List[VaccinationEvent]:
        """Get vaccination history, optionally filtered by disease"""
        query = self.db.query(VaccinationEvent).filter(
            VaccinationEvent.flock_id == flock_id
        )
        
        if disease_target:
            query = query.filter(VaccinationEvent.disease_target == disease_target)
        
        return query.order_by(VaccinationEvent.event_date.desc()).all()

    def has_received_vaccine(
        self, 
        flock_id: UUID, 
        vaccine_name: str
    ) -> bool:
        """Check if flock has received a specific vaccine"""
        count = self.db.query(VaccinationEvent).filter(
            and_(
                VaccinationEvent.flock_id == flock_id,
                VaccinationEvent.vaccine_name == vaccine_name
            )
        ).count()
        return count > 0