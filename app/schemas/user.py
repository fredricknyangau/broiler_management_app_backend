from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    """Base fields for User model."""
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    preferences: Optional[Dict[str, Any]] = {}


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for login credentials."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for user updates."""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """Schema for user profile response."""
    id: UUID4
    is_active: bool
    is_superuser: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[str] = None

