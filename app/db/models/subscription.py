from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    billing_period = Column(String, nullable=True) # "monthly" or "yearly"

    user = relationship("User", backref="subscriptions")

class SubscriptionPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscription_plans"

    plan_type = Column(String, unique=True, nullable=False, index=True) # STARTER, PROFESSIONAL, ENTERPRISE
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    monthly_price = Column(String, nullable=False, default="0")
    yearly_price = Column(String, nullable=False, default="0")
    features = Column(JSONB, nullable=False, default=[]) # List of feature keys
    is_active = Column(Boolean, default=True)
    popular = Column(Boolean, default=False)
    show_discount = Column(Boolean, default=True)
