from sqlalchemy import Column, String, Integer, Date, Text, DECIMAL, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class InventoryItem(Base, UUIDMixin, TimestampMixin):
    """
    Tracks farm inventory levels (feed, medicine, equipment).
    """
    __tablename__ = "inventory_items"

    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, doc="Item name")
    category = Column(String(50), nullable=False, doc="Category: feed, medicine, equipment, other")
    quantity = Column(DECIMAL(10, 2), nullable=False, default=0, doc="Current stock level")
    unit = Column(String(20), nullable=False, doc="Unit of measurement (kg, liters, pcs)")
    minimum_stock = Column(DECIMAL(10, 2), default=0, doc="Alert threshold level")
    cost_per_unit = Column(DECIMAL(10, 2), default=0, doc="Last known unit cost")
    last_restocked = Column(Date, nullable=True, doc="Date of last addition")
    notes = Column(Text, nullable=True)

    # Relationships
    farmer = relationship("User", backref="inventory_items")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="positive_quantity"),
    )
