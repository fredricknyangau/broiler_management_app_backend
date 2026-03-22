from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class FarmMember(Base, UUIDMixin, TimestampMixin):
    """
    Links users (Managers, Viewers) to a specific Farm Profile owned by a Farmer.
    Enables subscription/feature inheritance across workers.
    """
    __tablename__ = "farm_members"

    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    farm = relationship("Farm", backref="members")
    user = relationship("User", backref="memberships")

    def __repr__(self):
        return f"<FarmMember(farm_id='{self.farm_id}', user_id='{self.user_id}')>"
