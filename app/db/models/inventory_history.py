from sqlalchemy import Column, String, Integer, ForeignKey, Date, Enum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from app.db.base import Base, UUIDMixin, TimestampMixin
import enum

class InventoryAction(str, enum.Enum):
    PURCHASE = "purchase"
    CONSUMPTION = "consumption"
    ADJUSTMENT = "adjustment"
    RESTOCK = "restock"
    RETURN = "return"

class InventoryHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inventory_history"

    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    action = Column(String(50), nullable=False) # Enum: purchase, consumption, adjustment, etc.
    quantity_change = Column(DECIMAL(10, 2), nullable=False, doc="Positive or negative change")
    notes = Column(String(255), nullable=True)

    # Relationships
    inventory_item = relationship("InventoryItem", backref=backref("history_logs", cascade="all, delete-orphan"), passive_deletes=True)
    user = relationship("User")
