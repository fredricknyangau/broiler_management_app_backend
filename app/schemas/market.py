from pydantic import BaseModel, UUID4, Field
from datetime import date
from typing import Optional
from decimal import Decimal

class MarketPriceBase(BaseModel):
    price_date: date
    county: str = Field(..., max_length=100)
    town: Optional[str] = Field(None, max_length=100)
    price_per_kg: Decimal = Field(..., gt=0)
    price_per_bird: Optional[Decimal] = None
    source: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=255)

class MarketPriceCreate(MarketPriceBase):
    pass

class MarketPriceResponse(MarketPriceBase):
    id: UUID4

    class Config:
        from_attributes = True
