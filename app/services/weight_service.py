from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import WeightMeasurementEvent
from app.services.base_event_service import BaseEventService


class WeightMeasurementService(BaseEventService[WeightMeasurementEvent]):
    """Service for weight measurement operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(WeightMeasurementEvent, db)

    async def get_latest_weight(
        self, flock_id: UUID
    ) -> Optional[WeightMeasurementEvent]:
        """Get most recent weight measurement"""
        result = await self.db.execute(
            select(WeightMeasurementEvent)
            .filter(WeightMeasurementEvent.flock_id == flock_id)
            .order_by(WeightMeasurementEvent.event_date.desc())
        )
        return result.scalars().first()

    async def get_average_weight_trend(self, flock_id: UUID) -> List[dict]:
        """Get weight progression over time"""
        result = await self.db.execute(
            select(WeightMeasurementEvent)
            .filter(WeightMeasurementEvent.flock_id == flock_id)
            .order_by(WeightMeasurementEvent.event_date)
        )
        measurements = result.scalars().all()

        return [
            {
                "date": m.event_date,
                "average_weight_grams": float(m.average_weight_grams),
                "sample_size": m.sample_size,
            }
            for m in measurements
        ]

    async def calculate_growth_rate(
        self, flock_id: UUID, start_date: date, end_date: date
    ) -> Optional[float]:
        """Calculate average daily weight gain between two dates"""
        stmt_start = (
            select(WeightMeasurementEvent)
            .filter(
                WeightMeasurementEvent.flock_id == flock_id,
                WeightMeasurementEvent.event_date >= start_date,
            )
            .order_by(WeightMeasurementEvent.event_date)
        )

        result_start = await self.db.execute(stmt_start)
        start_measurement = result_start.scalars().first()

        stmt_end = (
            select(WeightMeasurementEvent)
            .filter(
                WeightMeasurementEvent.flock_id == flock_id,
                WeightMeasurementEvent.event_date <= end_date,
            )
            .order_by(WeightMeasurementEvent.event_date.desc())
        )

        result_end = await self.db.execute(stmt_end)
        end_measurement = result_end.scalars().first()

        if not start_measurement or not end_measurement:
            return None

        weight_diff = float(
            end_measurement.average_weight_grams
            - start_measurement.average_weight_grams
        )
        days_diff = (
            end_measurement.event_date - start_measurement.event_date
        ).days

        if days_diff <= 0:
            return None

        return round(weight_diff / days_diff, 2)

    async def is_growth_on_track(
        self,
        flock_id: UUID,
        days_old: int,
        expected_weight_grams: float,
        tolerance_percent: float = 10.0,
    ) -> Optional[bool]:
        """Check if current weight is within expected range"""
        latest = await self.get_latest_weight(flock_id)
        if not latest:
            return None

        actual_weight = float(latest.average_weight_grams)
        lower_bound = expected_weight_grams * (1 - tolerance_percent / 100)
        upper_bound = expected_weight_grams * (1 + tolerance_percent / 100)

        return lower_bound <= actual_weight <= upper_bound
