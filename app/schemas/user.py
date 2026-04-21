from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base fields for User model."""

    email: EmailStr | None = None
    full_name: str | None = None
    phone_number: str | None = None
    location: str | None = None
    county: str | None = None
    is_active: bool | None = True
    is_superuser: bool = False
    role: str | None = "FARMER"
    preferences: dict | None = {}


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str | None = Field(
        None, min_length=8, description="Password must be at least 8 characters"
    )


class UserLogin(BaseModel):
    """Schema for login credentials."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    location: str | None = None
    county: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    preferences: dict | None = None


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

    user_id: str | None = None


class OTPRequest(BaseModel):
    """Schema for requesting an OTP."""

    phone_number: str


class OTPVerify(BaseModel):
    """Schema for verifying an OTP."""

    phone_number: str
    code: str


class OTPSendResponse(BaseModel):
    """Response returned by POST /auth/send-otp.

    ``debug_code`` is only populated when ``DEBUG=True`` — never in production.
    """

    message: str
    debug_code: str | None = None
