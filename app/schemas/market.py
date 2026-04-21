from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import UUID4, BaseModel, Field


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
