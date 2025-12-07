from sqlalchemy import Column, String, Integer, Date, Time, Text, DECIMAL, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin
from datetime import datetime


class BaseEvent(UUIDMixin, TimestampMixin):
    """Abstract base for all event types.
    
    Provides common fields like ID, flock reference, date, and time.
    """
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, doc="Idempotency key provided by client")
    flock_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, default=datetime.now().time)

    __abstract__ = True


class MortalityEvent(Base, BaseEvent):
    """
    Records bird deaths or culls in a flock.
    """
    __tablename__ = "mortality_events"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False)
    count = Column(Integer, nullable=False, doc="Number of birds died/culled")
    cause = Column(String(100), doc="Presumed cause of death")
    symptoms = Column(Text, doc="Observed symptoms")
    action_taken = Column(Text, doc="Immediate actions taken")
    notes = Column(Text)

    # Relationships
    flock = relationship("Flock", back_populates="mortality_events")

    __table_args__ = (
        CheckConstraint("count > 0", name="positive_mortality_count"),
        Index("ix_mortality_events_flock_id", "flock_id"),
        Index("ix_mortality_events_event_date", "event_date"),
        Index("ix_mortality_events_event_id", "event_id", unique=True),
    )

    def __repr__(self):
        return f"<MortalityEvent(flock={self.flock_id}, date={self.event_date}, count={self.count})>"


class FeedConsumptionEvent(Base, BaseEvent):
    """
    Tracks feed usage for a flock.
    """
    __tablename__ = "feed_consumption_events"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False)
    feed_type = Column(String(50), doc="Type of feed: starter, grower, finisher")
    quantity_kg = Column(DECIMAL(10, 2), nullable=False, doc="Amount consumed in KG")
    cost_ksh = Column(DECIMAL(10, 2), doc="Cost of this feed record")
    supplier = Column(String(255), doc="Feed supplier name")
    notes = Column(Text)

    # Relationships
    flock = relationship("Flock", back_populates="feed_events")

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="positive_feed_quantity"),
        CheckConstraint("feed_type IN ('starter', 'grower', 'finisher')", name="valid_feed_type"),
        Index("ix_feed_consumption_events_flock_id", "flock_id"),
        Index("ix_feed_consumption_events_event_date", "event_date"),
        Index("ix_feed_consumption_events_event_id", "event_id", unique=True),
    )

    def __repr__(self):
        return f"<FeedConsumptionEvent(flock={self.flock_id}, date={self.event_date}, kg={self.quantity_kg})>"


class VaccinationEvent(Base, BaseEvent):
    """
    Records vaccination or medication administration.
    """
    __tablename__ = "vaccination_events"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False)
    vaccine_name = Column(String(100), nullable=False)
    disease_target = Column(String(100), nullable=False)
    administration_method = Column(String(50), doc="Method: drinking_water, eye_drop, injection, spray")
    dosage = Column(String(100), doc="Dosage per bird or total")
    administered_by = Column(String(255))
    batch_number = Column(String(100), doc="Vaccine batch number")
    next_due_date = Column(Date, index=True, doc="Date for next dose/booster")
    notes = Column(Text)

    # Relationships
    flock = relationship("Flock", back_populates="vaccination_events")

    __table_args__ = (
        CheckConstraint(
            "administration_method IN ('drinking_water', 'eye_drop', 'injection', 'spray')",
            name="valid_administration_method"
        ),
        Index("ix_vaccination_events_flock_id", "flock_id"),
        Index("ix_vaccination_events_event_date", "event_date"),
        Index("ix_vaccination_events_next_due_date", "next_due_date"),
        Index("ix_vaccination_events_event_id", "event_id", unique=True),
    )

    def __repr__(self):
        return f"<VaccinationEvent(flock={self.flock_id}, vaccine='{self.vaccine_name}', date={self.event_date})>"


class WeightMeasurementEvent(Base, BaseEvent):
    """
    Tracks the growth (weight) of the flock over time.
    """
    __tablename__ = "weight_measurement_events"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False)
    measurement_date = Column(Date, nullable=False)
    sample_size = Column(Integer, nullable=False, doc="Number of birds weighed")
    average_weight_grams = Column(DECIMAL(10, 2), nullable=False, doc="Average weight in grams")
    min_weight_grams = Column(DECIMAL(10, 2))
    max_weight_grams = Column(DECIMAL(10, 2))
    notes = Column(Text)

    # Relationships
    flock = relationship("Flock", back_populates="weight_events")

    __table_args__ = (
        CheckConstraint("sample_size > 0", name="positive_sample_size"),
        CheckConstraint("average_weight_grams > 0", name="positive_average_weight"),
        Index("ix_weight_measurement_events_flock_id", "flock_id"),
        Index("ix_weight_measurement_events_measurement_date", "measurement_date"),
        Index("ix_weight_measurement_events_event_id", "event_id", unique=True),
    )

    def __repr__(self):
        return f"<WeightMeasurementEvent(flock={self.flock_id}, date={self.measurement_date}, avg={self.average_weight_grams}g)>"
