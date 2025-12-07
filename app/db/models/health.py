from sqlalchemy import Column, String, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class VetConsultation(Base, UUIDMixin, TimestampMixin):
    """
    Records a veterinary consultation or health issue.
    """
    __tablename__ = "vet_consultations"

    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="SET NULL"), nullable=True)
    
    visit_date = Column(Date, nullable=False, index=True)
    issue = Column(String(255), nullable=False, doc="Main complaint or reason for visit")
    symptoms = Column(Text, doc="Observed symptoms")
    diagnosis = Column(Text, doc="Vet's diagnosis")
    treatment = Column(Text, doc="Prescribed treatment")
    vet_name = Column(String(255))
    vet_phone = Column(String(50))
    
    # Store image URLs/paths as array of strings
    images = Column(ARRAY(String), default=list)
    
    status = Column(String(50), default="pending", doc="pending, in_progress, resolved")
    notes = Column(Text)

    # Relationships
    farmer = relationship("User", backref="vet_consultations")
    flock = relationship("Flock", backref="vet_consultations")
