from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class Farm(Base, UUIDMixin, TimestampMixin):
    """
    Represents a Farm entity owned by a User.
    Allows Enterprise users to manage multiple locations/setups separately.
    """
    __tablename__ = "farms"

    name = Column(String(255), nullable=False, index=True, doc="Name/Label of the farm location")
    location = Column(String(255), nullable=True, doc="Geographic location or address details")
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, doc="The User ID who owns this farm")
    is_active = Column(Boolean, default=True, nullable=False, doc="Status flag for active management switches")

    # Relationships
    owner = relationship("User", backref="farms")

    def __repr__(self):
        return f"<Farm(name='{self.name}', owner_id='{self.owner_id}')>"
