from pydantic import BaseModel, Field, UUID4
from datetime import date, time
from typing import Optional, List
from enum import Enum


class ChickBehavior(str, Enum):
    """Observable behavior of the flock."""
    NORMAL = "normal"
    HUDDLING = "huddling"
    DISPERSED = "dispersed"
    PANTING = "panting"
    LETHARGIC = "lethargic"


class LitterCondition(str, Enum):
    """State of the bedding material."""
    DRY = "dry"
    DAMP = "damp"
    WET = "wet"
    CAKED = "caked"


class SupplyLevel(str, Enum):
    """Approximate level of feed or water."""
    FULL = "full"
    ADEQUATE = "adequate"
    LOW = "low"
    EMPTY = "empty"


class EventType(str, Enum):
    """Categorization of daily events."""
    MORTALITY = "mortality"
    FEED_CONSUMPTION = "feed_consumption"
    VACCINATION = "vaccination"
    WEIGHT_MEASUREMENT = "weight_measurement"


# Event schemas
class MortalityEventCreate(BaseModel):
    """Schema for reporting mortality."""
    event_id: UUID4 = Field(..., description="Client-generated idempotency key")
    count: int = Field(..., gt=0, description="Number of deaths")
    cause: Optional[str] = None
    symptoms: Optional[str] = None
    action_taken: Optional[str] = None
    notes: Optional[str] = None

class MortalityEventResponse(MortalityEventCreate):
    id: UUID4
    flock_id: UUID4
    event_date: date
    class Config:
        from_attributes = True

class MortalityEventUpdate(BaseModel):
    """Schema for updating mortality."""
    count: Optional[int] = Field(None, gt=0)
    cause: Optional[str] = None
    symptoms: Optional[str] = None
    action_taken: Optional[str] = None
    notes: Optional[str] = None

class FeedConsumptionEventCreate(BaseModel):
    """Schema for reporting feed usage."""
    event_id: UUID4
    feed_type: str = Field(..., pattern="^(starter|grower|finisher)$")
    quantity_kg: float = Field(..., gt=0)
    cost_ksh: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = None
    notes: Optional[str] = None

class FeedConsumptionEventUpdate(BaseModel):
    """Schema for updating feed usage."""
    feed_type: Optional[str] = Field(None, pattern="^(starter|grower|finisher)$")
    quantity_kg: Optional[float] = Field(None, gt=0)
    cost_ksh: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = None
    notes: Optional[str] = None

class FeedConsumptionEventResponse(FeedConsumptionEventCreate):
    id: UUID4
    flock_id: UUID4
    event_date: date
    class Config:
        from_attributes = True

class VaccinationEventCreate(BaseModel):
    """Schema for reporting vaccination."""
    event_id: UUID4
    vaccine_name: str
    disease_target: str
    administration_method: str = Field(..., pattern="^(drinking_water|eye_drop|injection|spray)$")
    dosage: Optional[str] = None
    administered_by: Optional[str] = None
    batch_number: Optional[str] = None
    next_due_date: Optional[date] = None
    notes: Optional[str] = None

class VaccinationEventUpdate(BaseModel):
    """Schema for updating vaccination."""
    vaccine_name: Optional[str] = None
    disease_target: Optional[str] = None
    administration_method: Optional[str] = Field(None, pattern="^(drinking_water|eye_drop|injection|spray)$")
    dosage: Optional[str] = None
    administered_by: Optional[str] = None
    batch_number: Optional[str] = None
    next_due_date: Optional[date] = None
    notes: Optional[str] = None

class VaccinationEventResponse(VaccinationEventCreate):
    id: UUID4
    flock_id: UUID4
    event_date: date
    class Config:
        from_attributes = True

class WeightMeasurementEventCreate(BaseModel):
    """Schema for reporting weight sampling."""
    event_id: UUID4
    sample_size: int = Field(..., gt=0)
    average_weight_grams: float = Field(..., gt=0)
    min_weight_grams: Optional[float] = Field(None, gt=0)
    max_weight_grams: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None

class WeightMeasurementEventUpdate(BaseModel):
    """Schema for updating weight sampling."""
    sample_size: Optional[int] = Field(None, gt=0)
    average_weight_grams: Optional[float] = Field(None, gt=0)
    min_weight_grams: Optional[float] = Field(None, gt=0)
    max_weight_grams: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None

class WeightMeasurementEventResponse(WeightMeasurementEventCreate):
    id: UUID4
    flock_id: UUID4
    event_date: date
    class Config:
        from_attributes = True


# Union type for events
class EventData(BaseModel):
    """Polymorphic container for specific event data."""
    type: EventType
    data: MortalityEventCreate | FeedConsumptionEventCreate | VaccinationEventCreate | WeightMeasurementEventCreate


# Daily check schema (batch endpoint)
class DailyCheckCreate(BaseModel):
    """Batch submission of daily check with multiple events.
    
    Acts as an aggregate root for recording daily observations and related events.
    """
    flock_id: UUID4
    check_date: date = Field(default_factory=date.today)
    check_time: Optional[time] = None
    
    # Observations
    temperature_celsius: Optional[float] = Field(None, ge=-10, le=50)
    humidity_percent: Optional[float] = Field(None, ge=0, le=100)
    chick_behavior: Optional[ChickBehavior] = None
    litter_condition: Optional[LitterCondition] = None
    feed_level: Optional[SupplyLevel] = None
    water_level: Optional[SupplyLevel] = None
    general_notes: Optional[str] = None
    
    # Events that occurred today
    events: List[EventData] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "flock_id": "550e8400-e29b-41d4-a716-446655440000",
                "check_date": "2025-12-06",
                "temperature_celsius": 28.5,
                "humidity_percent": 65,
                "chick_behavior": "normal",
                "litter_condition": "dry",
                "feed_level": "adequate",
                "water_level": "full",
                "general_notes": "Flock appears healthy",
                "events": [
                    {
                        "type": "feed_consumption",
                        "data": {
                            "event_id": "650e8400-e29b-41d4-a716-446655440001",
                            "feed_type": "starter",
                            "quantity_kg": 3.5,
                            "cost_ksh": 450.0
                        }
                    }
                ]
            }
        }


class DailyCheckResponse(BaseModel):
    """Response summary after processing daily check."""
    check_id: UUID4
    flock_id: UUID4
    check_date: date
    events_processed: int
    alerts_triggered: List[dict]
    
    class Config:
        from_attributes = True
