from sqlalchemy import Column, String, Text, DECIMAL, Boolean, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.db.base import Base, TimestampMixin, UUIDMixin

class SupplierCategory(str, enum.Enum):
    FEED = "feed"
    CHICKS = "chicks"
    MEDICINE = "medicine"
    EQUIPMENT = "equipment"
    OTHER = "other"

class CustomerType(str, enum.Enum):
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    OTHER = "other"

class EmployeeRole(str, enum.Enum):
    MANAGER = "manager"
    WORKER = "worker"
    VET = "vet"
    OTHER = "other"

class Supplier(Base, UUIDMixin, TimestampMixin):
    """
    Suppliers for farm inputs (feed, chicks, etc.)
    """
    __tablename__ = "suppliers"

    name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    category = Column(SAEnum(SupplierCategory), nullable=False, default=SupplierCategory.OTHER)
    notes = Column(Text, nullable=True)

    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", backref="suppliers")

class Customer(Base, UUIDMixin, TimestampMixin):
    """
    Customers who buy farm produce.
    """
    __tablename__ = "customers"

    name = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(50), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    customer_type = Column(SAEnum(CustomerType), nullable=False, default=CustomerType.RETAIL)
    notes = Column(Text, nullable=True)

    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", backref="customers")

class Employee(Base, UUIDMixin, TimestampMixin):
    """
    Farm staff/employees.
    """
    __tablename__ = "employees"

    name = Column(String(255), nullable=False, index=True)
    role = Column(SAEnum(EmployeeRole), nullable=False, default=EmployeeRole.WORKER)
    phone_number = Column(String(50), nullable=True)
    salary = Column(DECIMAL(10, 2), nullable=True)
    start_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", backref="employees")
