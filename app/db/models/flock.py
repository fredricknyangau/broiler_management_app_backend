from sqlalchemy import Column, String, Integer, Date, Text, CheckConstraint, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class Flock(Base, UUIDMixin, TimestampMixin):
    """
    Represents a flock (batch) of birds in the system.
    
    A flock is the central entity for tracking production. It has a lifecycle from 
    placement (active) to completion (sold/culled/completed).
    """
    __tablename__ = "flocks"

    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic Details
    name = Column(String(255), nullable=False, doc="Name or identifier of the batch (e.g., 'Batch A')")
    breed = Column(String(100), doc="Breed of the birds (e.g., 'Ross 308', 'Cobb 500')")
    hatchery_source = Column(String(255), doc="Source hatchery where chicks were purchased")
    source_location = Column(String(255), doc="Specific location/house where chicks are placed")

    # Dates & Counts
    start_date = Column(Date, nullable=False, doc="Date when chicks were placed")
    initial_count = Column(Integer, nullable=False, doc="Number of chicks originally placed")
    expected_end_date = Column(Date, doc="Projected date for harvesting")
    
    # Financials
    cost_per_bird = Column(DECIMAL(10, 2), default=0.00, doc="Cost per individual chick at purchase")
    total_acquisition_cost = Column(DECIMAL(10, 2), default=0.00, doc="Total cost of acquiring the flock")
    
    # Status
    status = Column(String(50), default="active", nullable=False, index=True, doc="Current status: active, completed, sold, culled, terminated")
    notes = Column(Text, doc="General notes about the flock")

    # Relationships
    farmer = relationship("User", back_populates="flocks")
    daily_checks = relationship("DailyCheck", back_populates="flock", cascade="all, delete-orphan")
    mortality_events = relationship("MortalityEvent", back_populates="flock", cascade="all, delete-orphan")
    feed_events = relationship("FeedConsumptionEvent", back_populates="flock", cascade="all, delete-orphan")
    vaccination_events = relationship("VaccinationEvent", back_populates="flock", cascade="all, delete-orphan")
    weight_events = relationship("WeightMeasurementEvent", back_populates="flock", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="flock", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("initial_count > 0", name="positive_initial_count"),
        CheckConstraint("status IN ('active', 'completed', 'sold', 'culled', 'terminated')", name="valid_status"),
    )

    def __repr__(self):
        return f"<Flock(name='{self.name}', count={self.initial_count}, status='{self.status}')>"