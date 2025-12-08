from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.db.models.people import SupplierCategory, CustomerType, EmployeeRole

# Supplier Schemas
class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    category: SupplierCategory = SupplierCategory.OTHER
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(SupplierBase):
    name: Optional[str] = None

class Supplier(SupplierBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

# Customer Schemas
class CustomerBase(BaseModel):
    name: str
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    customer_type: CustomerType = CustomerType.RETAIL
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    name: Optional[str] = None

class Customer(CustomerBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True

# Employee Schemas
class EmployeeBase(BaseModel):
    name: str
    role: EmployeeRole = EmployeeRole.WORKER
    phone_number: Optional[str] = None
    salary: Optional[Decimal] = None
    start_date: Optional[date] = None
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    name: Optional[str] = None

class Employee(EmployeeBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True
