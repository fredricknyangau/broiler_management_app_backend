from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class SubscriptionCreate(BaseModel):
    # plan_type: "PROFESSIONAL" | "ENTERPRISE" (STARTER is default/free)
    plan_type: str
    billing_period: str  # "monthly" | "yearly"
    phone_number: str  # Format: 2547XXXXXXXX


class MpesaCallbackById(BaseModel):
    pass


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_type: str
    status: str
    start_date: datetime | None
    end_date: datetime | None
    mpesa_reference: str | None
    billing_period: str | None
    checkout_request_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlanResponse(BaseModel):
    id: UUID
    plan_type: str
    name: str
    description: str | None
    monthly_price: Decimal
    yearly_price: Decimal
    features: list[str]
    is_active: bool
    popular: bool
    show_discount: bool

    @field_validator("is_active", mode="before")
    @classmethod
    def parse_is_active(cls, v):
        return True if v is None else v

    @field_validator("popular", mode="before")
    @classmethod
    def parse_popular(cls, v):
        return False if v is None else v

    @field_validator("show_discount", mode="before")
    @classmethod
    def parse_show_discount(cls, v):
        return True if v is None else v

    model_config = ConfigDict(from_attributes=True)


class PlanCreate(BaseModel):
    plan_type: str
    name: str
    description: str | None = None
    monthly_price: Decimal = Decimal("0")
    yearly_price: Decimal = Decimal("0")
    features: list[str] = []
    is_active: bool = True
    popular: bool = False
    show_discount: bool = True


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    monthly_price: Decimal | None = None
    yearly_price: Decimal | None = None
    features: list[str] | None = None
    is_active: bool | None = None
    popular: bool | None = None
    show_discount: bool | None = None


class SubscriptionOverride(BaseModel):
    plan_type: str
    end_date: datetime | None = None
    amount: Decimal | None = Decimal("0")
    status: str | None = "ACTIVE"


class MpesaCallbackResponse(BaseModel):
    """Shape of the JSON body KukuFlow returns to Safaricom after processing a callback.

    Safaricom ignores the response body beyond confirming an HTTP 200; this schema
    exists so FastAPI generates accurate OpenAPI docs and we don't accidentally
    change the shape without noticing.
    """

    status: str  # "processed" | "ignored" | "error"
    result_code: int | None = None
    reason: str | None = None
