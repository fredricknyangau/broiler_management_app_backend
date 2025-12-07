from pydantic import BaseModel, Field, UUID4, validator
from datetime import date
from typing import Optional
from decimal import Decimal

class ExpenditureBase(BaseModel):
    """Base fields for Expenditure."""
    date: date
    category: str = Field(..., max_length=50)
    description: str = Field(..., max_length=255)
    amount: Decimal = Field(..., ge=0)
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    mpesa_transaction_id: Optional[str] = None

class ExpenditureCreate(ExpenditureBase):
    """Schema for creating a new expenditure."""
    flock_id: Optional[UUID4] = None

class ExpenditureUpdate(BaseModel):
    """Schema for updating an expenditure."""
    date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0)
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    mpesa_transaction_id: Optional[str] = None

class ExpenditureResponse(ExpenditureBase):
    """Schema for expenditure response."""
    id: UUID4
    flock_id: Optional[UUID4]
    farmer_id: UUID4
    
    class Config:
        from_attributes = True

class SaleBase(BaseModel):
    """Base fields for Sale."""
    date: date
    quantity: int = Field(..., gt=0)
    price_per_bird: Decimal = Field(..., ge=0)
    total_amount: Decimal = Field(..., ge=0)
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None
    notes: Optional[str] = None
    mpesa_transaction_id: Optional[str] = None
    average_weight_grams: Optional[Decimal] = None

class SaleCreate(SaleBase):
    """Schema for recording a new sale."""
    flock_id: UUID4

class SaleUpdate(BaseModel):
    """Schema for updating a sale."""
    date: Optional[date] = None
    quantity: Optional[int] = Field(None, gt=0)
    price_per_bird: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None
    notes: Optional[str] = None
    mpesa_transaction_id: Optional[str] = None
    average_weight_grams: Optional[Decimal] = None

class SaleResponse(SaleBase):
    """Schema for sale response."""
    id: UUID4
    flock_id: UUID4
    farmer_id: UUID4
    
    class Config:
        from_attributes = True
