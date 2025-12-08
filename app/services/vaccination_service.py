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

    def generate_schedule(self, flock_id: UUID, start_date: date) -> List[VaccinationEvent]:
        """Generate standard vaccination schedule for a new flock"""
        from app.core.vaccination_schedule import STANDARD_SCHEDULE
        from uuid import uuid4
        
        events = []
        for item in STANDARD_SCHEDULE:
            due_date = start_date + timedelta(days=item["day"])
            
            # Create event record (planned)
            event = VaccinationEvent(
                event_id=uuid4(),
                flock_id=flock_id,
                event_date=due_date, # For planned events, we use due date as event date until completed
                vaccine_name=item["vaccine_name"],
                disease_target=item["disease_target"],
                administration_method=item["method"],
                next_due_date=due_date,
                notes=item["notes"]
            )
            self.db.add(event)
            events.append(event)
            
        self.db.commit()
        return events