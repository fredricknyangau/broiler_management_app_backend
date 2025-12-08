from sqlalchemy import Column, String, Integer, Date, Text, DECIMAL, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

class Expenditure(Base, UUIDMixin, TimestampMixin):
    """
    Records an expense related to the farm or a specific flock.
    """
    __tablename__ = "expenditures"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=True, index=True, doc="Optional link to specific flock")
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, doc="Date of expense")
    category = Column(String(50), nullable=False, doc="Category: feed, medicine, equipment, etc.")
    description = Column(String(255), nullable=False, doc="Detailed description")
    amount = Column(DECIMAL(10, 2), nullable=False, doc="Cost in local currency")
    quantity = Column(DECIMAL(10, 2), nullable=True)
    unit = Column(String(20), nullable=True)
    receipt_image = Column(String(255), nullable=True, doc="URL/path to receipt image")
    mpesa_transaction_id = Column(String(50), nullable=True)

    # Relationships
    flock = relationship("Flock", backref="expenditures")
    farmer = relationship("User", backref="expenditures")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="positive_amount"),
    )

    # New Foreign Key
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier = relationship("Supplier", backref="expenditures")

class Sale(Base, UUIDMixin, TimestampMixin):
    """
    Records a sale of birds (revenue).
    """
    __tablename__ = "sales"

    flock_id = Column(UUID(as_uuid=True), ForeignKey("flocks.id", ondelete="CASCADE"), nullable=False, index=True)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, doc="Date of sale")
    quantity = Column(Integer, nullable=False, doc="Number of birds sold")
    price_per_bird = Column(DECIMAL(10, 2), nullable=False, doc="Unit price")
    total_amount = Column(DECIMAL(10, 2), nullable=False, doc="Total revenue")
    buyer_name = Column(String(255), nullable=True)
    buyer_phone = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    mpesa_transaction_id = Column(String(50), nullable=True)
    average_weight_grams = Column(DECIMAL(10, 2), nullable=True, doc="Avg weight of birds sold")
    
    # New Foreign Key
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer = relationship("Customer", backref="sales")

    # Relationships
    flock = relationship("Flock", backref="sales")
    farmer = relationship("User", backref="sales")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("total_amount >= 0", name="positive_total_amount"),
    )
