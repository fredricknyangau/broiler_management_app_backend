from sqlalchemy import Column, String, Date, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class BiosecurityCheck(Base, UUIDMixin, TimestampMixin):
    """
    Daily log of biosecurity compliance and hygiene measures.
    """
    __tablename__ = "biosecurity_checks"

    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, doc="Date of check")
    items = Column(JSON, nullable=False, doc="List of completion status: [{task: str, completed: bool, notes: str}]")
    notes = Column(Text, nullable=True, doc="General observations")
    completed_by = Column(String(255), nullable=True, doc="Person who performed the check")

    # Relationships
    farmer = relationship("User", backref="biosecurity_checks")
