from sqlalchemy import Column, String, Date, Time, Text, DECIMAL, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class DailyCheck(Base, UUIDMixin, TimestampMixin):
    """
    Daily observation record for a flock.
    
    Includes environmental data (temp, humidity) and qualitative assessments (behavior, litter).
    """
    __tablename__ = "daily_checks"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False, index=True)
    check_date = Column(Date, nullable=False, index=True, doc="Date of observation")
    check_time = Column(Time, doc="Time of observation")
    temperature_celsius = Column(DECIMAL(4, 2), doc="Current temperature in Celsius")
    humidity_percent = Column(DECIMAL(4, 2), doc="Relative humidity percentage")
    chick_behavior = Column(String(50), doc="Qualitative assessment: normal, huddling, panting...")
    litter_condition = Column(String(50), doc="Condition of bedding: dry, wet, caked...")
    feed_level = Column(String(50), doc="Status of feed availability")
    water_level = Column(String(50), doc="Status of water availability")
    general_notes = Column(Text, doc="Any other observations")
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    flock = relationship("Flock", back_populates="daily_checks")

    __table_args__ = (
        UniqueConstraint("flock_id", "check_date", name="uq_flock_daily_check"),
        CheckConstraint(
            "chick_behavior IN ('normal', 'huddling', 'dispersed', 'panting', 'lethargic')",
            name="valid_chick_behavior"
        ),
        CheckConstraint(
            "litter_condition IN ('dry', 'damp', 'wet', 'caked')",
            name="valid_litter_condition"
        ),
        CheckConstraint(
            "feed_level IN ('full', 'adequate', 'low', 'empty')",
            name="valid_feed_level"
        ),
        CheckConstraint(
            "water_level IN ('full', 'adequate', 'low', 'empty')",
            name="valid_water_level"
        ),
    )

    def __repr__(self):
        return f"<DailyCheck(flock={self.flock_id}, date={self.check_date}, temp={self.temperature_celsius})>"
