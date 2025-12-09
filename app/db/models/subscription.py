from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base, TimestampMixin, UUIDMixin

class PlanType(str, enum.Enum):
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"

class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_type = Column(String, nullable=False, default=PlanType.STARTER) # Stored as string for flexibility
    status = Column(String, nullable=False, default=SubscriptionStatus.PENDING)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    amount = Column(String, nullable=True) # e.g. "500.00"
    mpesa_reference = Column(String, nullable=True, unique=True, index=True)
    checkout_request_id = Column(String, nullable=True, unique=True, index=True)
    phone_number = Column(String, nullable=True)

    user = relationship("User", backref="subscriptions")
