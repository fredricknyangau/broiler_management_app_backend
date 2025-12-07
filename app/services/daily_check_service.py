from typing import Dict, Any, List
from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models.daily_check import DailyCheck
from app.db.models.events import (
    MortalityEvent,
    FeedConsumptionEvent,
    VaccinationEvent,
    WeightMeasurementEvent
)
from app.services.mortality_service import MortalityEventService
from app.services.feed_service import FeedConsumptionService
from app.services.vaccination_service import VaccinationService
from app.services.weight_service import WeightMeasurementService


class DailyCheckService:
    """Service for processing daily checks and events"""
    
    def __init__(self, db: Session):
        self.db = db
        self.mortality_service = MortalityEventService(db)
        self.feed_service = FeedConsumptionService(db)
        self.vaccination_service = VaccinationService(db)
        self.weight_service = WeightMeasurementService(db)
    
    def process_daily_check(
        self,
        flock_id: UUID,
        check_date: date,
        observations: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process daily check submission:
        1. Create/update daily check record
        2. Process all events with idempotency
        3. Return summary
        """
        # Create or update daily check
        check = self._upsert_daily_check(flock_id, check_date, observations)
        
        # Process events
        events_processed = 0
        for event in events:
            # Handle Pydantic model inputs
            if hasattr(event, "model_dump"):
                event_dict = event.model_dump()
                event_type = event_dict.get("type")
                event_data = event_dict.get("data")
            else:
                event_type = event.get("type")
                event_data = event.get("data")
            
            if not event_type or not event_data:
                continue
            
            # Add common fields
            event_data["flock_id"] = flock_id
            event_data["event_date"] = check_date
            
            # Route to appropriate service
            if event_type == "mortality":
                self.mortality_service.create_event(event_data)
                events_processed += 1
            elif event_type == "feed_consumption":
                self.feed_service.create_event(event_data)
                events_processed += 1
            elif event_type == "vaccination":
                self.vaccination_service.create_event(event_data)
                events_processed += 1
            elif event_type == "weight_measurement":
                self.weight_service.create_event(event_data)
                events_processed += 1
        
        return {
            "check_id": check.id,
            "events_processed": events_processed
        }
    
    def _upsert_daily_check(
        self,
        flock_id: UUID,
        check_date: date,
        observations: Dict[str, Any]
    ) -> DailyCheck:
        """Create or update daily check (idempotent)"""
        # Check for existing
        existing = self.db.query(DailyCheck).filter(
            DailyCheck.flock_id == flock_id,
            DailyCheck.check_date == check_date
        ).first()
        
        if existing:
            # Update existing
            for key, value in observations.items():
                if value is not None:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new
        check = DailyCheck(
            flock_id=flock_id,
            check_date=check_date,
            **observations
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check
