from uuid import UUID
from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.events import WeightMeasurementEvent
from app.services.base_event_service import BaseEventService


class WeightMeasurementService(BaseEventService[WeightMeasurementEvent]):
    """Service for weight measurement operations"""

    def __init__(self, db: Session):
        super().__init__(WeightMeasurementEvent, db)

    def get_latest_weight(self, flock_id: UUID) -> Optional[WeightMeasurementEvent]:
        """Get most recent weight measurement"""
        return self.db.query(WeightMeasurementEvent).filter(
            WeightMeasurementEvent.flock_id == flock_id
        ).order_by(
            WeightMeasurementEvent.measurement_date.desc()
        ).first()

    def get_average_weight_trend(self, flock_id: UUID) -> List[dict]:
        """Get weight progression over time"""
        measurements = self.db.query(WeightMeasurementEvent).filter(
            WeightMeasurementEvent.flock_id == flock_id
        ).order_by(
            WeightMeasurementEvent.measurement_date
        ).all()
        
        return [
            {
                "date": m.measurement_date,
                "average_weight_grams": float(m.average_weight_grams),
                "sample_size": m.sample_size
            }
            for m in measurements
        ]

    def calculate_growth_rate(
        self, 
        flock_id: UUID, 
        start_date: date,
        end_date: date
    ) -> Optional[float]:
        """Calculate average daily weight gain between two dates"""
        start_measurement = self.db.query(WeightMeasurementEvent).filter(
            WeightMeasurementEvent.flock_id == flock_id,
            WeightMeasurementEvent.measurement_date >= start_date
        ).order_by(WeightMeasurementEvent.measurement_date).first()
        
        end_measurement = self.db.query(WeightMeasurementEvent).filter(
            WeightMeasurementEvent.flock_id == flock_id,
            WeightMeasurementEvent.measurement_date <= end_date
        ).order_by(WeightMeasurementEvent.measurement_date.desc()).first()
        
        if not start_measurement or not end_measurement:
            return None
        
        weight_diff = float(end_measurement.average_weight_grams - start_measurement.average_weight_grams)
        days_diff = (end_measurement.measurement_date - start_measurement.measurement_date).days
        
        if days_diff <= 0:
            return None
        
        return round(weight_diff / days_diff, 2)

    def is_growth_on_track(
        self, 
        flock_id: UUID, 
        days_old: int,
        expected_weight_grams: float,
        tolerance_percent: float = 10.0
    ) -> Optional[bool]:
        """Check if current weight is within expected range"""
        latest = self.get_latest_weight(flock_id)
        if not latest:
            return None
        
        actual_weight = float(latest.average_weight_grams)
        lower_bound = expected_weight_grams * (1 - tolerance_percent / 100)
        upper_bound = expected_weight_grams * (1 + tolerance_percent / 100)
        
        return lower_bound <= actual_weight <= upper_bound