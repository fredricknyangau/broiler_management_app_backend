from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class SubscriptionCreate(BaseModel):
    # plan_type: "PROFESSIONAL" | "ENTERPRISE" (STARTER is default/free)
    plan_type: str 
    billing_period: str # "monthly" | "yearly"
    phone_number: str # Format: 2547XXXXXXXX

class MpesaCallbackById(BaseModel):
    # Simplified structure for internal manual updates if needed, 
    # but initially we'll handle the raw JSON from Safaricom in the service
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
