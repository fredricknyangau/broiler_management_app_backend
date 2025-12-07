from pydantic import BaseModel, UUID4, Field
from datetime import date
from typing import Optional, List

class VetConsultationBase(BaseModel):
    visit_date: date
    issue: str = Field(..., max_length=255)
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    vet_name: Optional[str] = Field(None, max_length=255)
    vet_phone: Optional[str] = Field(None, max_length=50)
    images: List[str] = []
    status: str = Field("pending", pattern="^(pending|in_progress|resolved)$")
    notes: Optional[str] = None

class VetConsultationCreate(VetConsultationBase):
    flock_id: Optional[UUID4] = None

class VetConsultationResponse(VetConsultationBase):
    id: UUID4
    farmer_id: UUID4
    flock_id: Optional[UUID4]

    class Config:
        from_attributes = True
