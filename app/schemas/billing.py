from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class SubscriptionCreate(BaseModel):
    # plan_type: "PROFESSIONAL" | "ENTERPRISE" (STARTER is default/free)
    plan_type: str 
    billing_period: str # "monthly" | "yearly"
    phone_number: str # Format: 2547XXXXXXXX

class MpesaCallbackById(BaseModel):
    pass

class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_type: str
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    mpesa_reference: Optional[str]
    billing_period: Optional[str]

    class Config:
        from_attributes = True

class PlanResponse(BaseModel):
    id: UUID
    plan_type: str
    name: str
    description: Optional[str]
    monthly_price: Decimal
    yearly_price: Decimal
    features: List[str]
    is_active: bool
    popular: bool
    show_discount: bool

    @field_validator('is_active', mode='before')
    @classmethod
    def parse_is_active(cls, v):
        return True if v is None else v

    @field_validator('popular', mode='before')
    @classmethod
    def parse_popular(cls, v):
        return False if v is None else v

    @field_validator('show_discount', mode='before')
    @classmethod
    def parse_show_discount(cls, v):
        return True if v is None else v

    class Config:
        from_attributes = True

class PlanCreate(BaseModel):
    plan_type: str
    name: str
    description: Optional[str] = None
    monthly_price: Decimal = Decimal("0")
    yearly_price: Decimal = Decimal("0")
    features: List[str] = []
    is_active: bool = True
    popular: bool = False
    show_discount: bool = True

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[Decimal] = None
    yearly_price: Optional[Decimal] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    popular: Optional[bool] = None
    show_discount: Optional[bool] = None

class SubscriptionOverride(BaseModel):
    plan_type: str
    end_date: Optional[datetime] = None
    amount: Optional[Decimal] = Decimal("0")
    status: Optional[str] = "ACTIVE"
