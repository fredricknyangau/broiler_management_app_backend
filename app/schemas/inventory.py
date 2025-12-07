from pydantic import BaseModel, Field, UUID4
from datetime import date
from typing import Optional
from decimal import Decimal

class InventoryItemBase(BaseModel):
    """Base fields for Inventory Item."""
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=50)
    quantity: Decimal = Field(0, ge=0)
    unit: str = Field(..., max_length=20)
    minimum_stock: Decimal = Field(0, ge=0)
    cost_per_unit: Decimal = Field(0, ge=0)
    last_restocked: Optional[date] = None
    notes: Optional[str] = None

class InventoryItemCreate(InventoryItemBase):
    """Schema for adding new inventory item."""
    pass

class InventoryItemUpdate(BaseModel):
    """Schema for updating an inventory item."""
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    cost_per_unit: Optional[Decimal] = Field(None, ge=0)
    last_restocked: Optional[date] = None
    notes: Optional[str] = None

class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item response."""
    id: UUID4
    farmer_id: UUID4
    
    class Config:
        from_attributes = True
