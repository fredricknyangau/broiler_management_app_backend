from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    """Base fields for User model."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    role: Optional[str] = "FARMER"
    preferences: Optional[Dict[str, Any]] = {}


class UserCreate(UserBase):
    """Schema for user registration."""
    password: Optional[str] = Field(None, min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for login credentials."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for user updates."""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """Schema for user profile response."""
    id: UUID4
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[str] = None


class OTPRequest(BaseModel):
    """Schema for requesting an OTP."""
    phone_number: str


class OTPVerify(BaseModel):
    """Schema for verifying an OTP."""
    phone_number: str
    code: str

