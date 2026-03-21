from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

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

    class Config:
        from_attributes = True

class PlanResponse(BaseModel):
    id: str # e.g., "STARTER", "PROFESSIONAL", "ENTERPRISE"
    name: str # e.g., "Starter", "Professional"
    description: str
    monthly_price: str # e.g., "Free", "KES 500"
    annual_price: Optional[str] = None # e.g., "KES 5,000"
    period: str # e.g., "/ monthly", "/ forever"
    features: List[str]
    cta: str # e.g., "Get Started Free"
    popular: bool
