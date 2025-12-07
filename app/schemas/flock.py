from pydantic import BaseModel, Field, UUID4
from datetime import date
from typing import Optional

class FlockBase(BaseModel):
    """Base properties shared by create, update, and response schemas."""
    name: str = Field(..., max_length=255)
    breed: Optional[str] = Field(None, max_length=100)
    hatchery_source: Optional[str] = Field(None, max_length=255)
    source_location: Optional[str] = Field(None, max_length=255)
    start_date: date
    initial_count: int = Field(..., gt=0, description="Initial number of birds")
    expected_end_date: Optional[date] = None
    cost_per_bird: Optional[float] = 0.0
    total_acquisition_cost: Optional[float] = 0.0
    status: str = Field("active", pattern="^(active|completed|sold|culled|terminated)$")
    notes: Optional[str] = None

class FlockCreate(FlockBase):
    """Properties to receive on flock creation."""
    pass

class FlockUpdate(BaseModel):
    """Properties to receive on flock update."""
    name: Optional[str] = Field(None, max_length=255)
    breed: Optional[str] = Field(None, max_length=100)
    hatchery_source: Optional[str] = Field(None, max_length=255)
    source_location: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    initial_count: Optional[int] = Field(None, gt=0)
    cost_per_bird: Optional[float] = Field(None, ge=0)
    total_acquisition_cost: Optional[float] = Field(None, ge=0)
    expected_end_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|sold|culled|terminated)$")
    notes: Optional[str] = None

class FlockResponse(FlockBase):
    """Properties to return to client."""
    id: UUID4
    farmer_id: UUID4
    
    class Config:
        from_attributes = True
