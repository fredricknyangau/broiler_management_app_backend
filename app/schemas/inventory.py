import datetime
from decimal import Decimal
from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict, Field


class InventoryItemBase(BaseModel):
    """Base fields for Inventory Item."""

    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=50)
    quantity: Decimal = Field(0, ge=0)
    unit: str = Field(..., max_length=20)
    minimum_stock: Decimal = Field(0, ge=0)
    cost_per_unit: Decimal = Field(0, ge=0)
    last_restocked: Optional[datetime.date] = None
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
    last_restocked: Optional[datetime.date] = None
    notes: Optional[str] = None


class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item response."""

    id: UUID4
    farmer_id: UUID4

    model_config = ConfigDict(from_attributes=True)


class InventoryHistoryResponse(BaseModel):
    """Schema for inventory history log."""

    id: UUID4
    inventory_item_id: UUID4
    user_id: UUID4
    date: datetime.date
    action: str
    quantity_change: Decimal
    notes: Optional[str] = None
    created_at: datetime.date

    model_config = ConfigDict(from_attributes=True)
