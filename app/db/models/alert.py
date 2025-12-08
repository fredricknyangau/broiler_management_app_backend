from sqlalchemy import Column, String, Text, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin
from datetime import datetime


class Alert(Base, UUIDMixin, TimestampMixin):
    """
    System-generated alerts for flock health or inventory issues.
    """
    __tablename__ = "alerts"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(100), nullable=False, doc="Type: disease_risk, low_feed, weight_deviation...")
    severity = Column(String(20), nullable=False, doc="Severity: low, medium, high, critical")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="active", nullable=False, doc="active, acknowledged, resolved")
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    alert_metadata = Column(JSONB, doc="Contextual data (e.g. sensor readings, inventory id)")

    # Relationships
    flock = relationship("Flock", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_flock_id", "flock_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_triggered_at", "triggered_at"),
    )

    def __repr__(self):
        return f"<Alert(type='{self.alert_type}', severity='{self.severity}', status='{self.status}')>"
