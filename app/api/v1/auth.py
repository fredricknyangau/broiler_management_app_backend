import base64
import json
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (get_current_user, get_db, set_rls_bypass)
from app.config import settings
from app.core.security import create_access_token
from app.db.models.user import User
from app.schemas.user import (OTPRequest, OTPSendResponse, OTPVerify, Token,
                              UserCreate, UserLogin, UserResponse, UserUpdate)
from app.services.otp_service import OTPDeliveryError, OTPService
from app.services.user_service import UserService

router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new farmer account.

    - **email**: Valid email address (will be used for login)
    - **password**: Minimum 8 characters
    - **full_name**: Farmer's full name
    - **phone_number**: Contact number (e.g., +254712345678)
    - **location**: Farm location
    """
    service = UserService(db)

    # Enable bypass for the lookup/creation
    await set_rls_bypass(db)

    try:
        user = await service.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            location=user_data.location,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
        Login to get access token.

        Returns a JWT token that should be included in the Authorization header
        for all subsequent requests:
    ```
        Authorization: Bearer <token>
    ```

        Token expires after 7 days by default.
    """
    service = UserService(db)

    # Enable bypass for initial authentication lookup
    await set_rls_bypass(db)

    # Authenticate user
    user = await service.authenticate(credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile.

    Requires authentication (JWT token in Authorization header).
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile.

    Requires authentication.
    """
    service = UserService(db)

    # create dict from pydantic model, excluding None values
    update_data = user_update.model_dump(exclude_unset=True)

    updated_user = await service.update_user(
        user_id=str(current_user.id), **update_data
    )

    return updated_user


@router.post("/send-otp", response_model=OTPSendResponse)
async def send_otp(request: OTPRequest):
    """
    Send a 4-digit OTP code to the provided phone number.
    The OTP is delivered via SMS. The code is never echoed in the response.
    """
    service = OTPService()
    phone_number = request.phone_number.strip()

    try:
        code = await service.send_otp(phone_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except OTPDeliveryError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    response = OTPSendResponse(message="OTP sent successfully")
    # Safety valve: only expose OTP in local development — NEVER in production
    if settings.DEBUG:
        response.debug_code = code
    return response


@router.post("/verify-otp", response_model=Token)
async def verify_otp(request: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify the OTP code.
    If valid, logs the user in (creates account if new phone number).
    """
    otp_service = OTPService()
    phone_number = otp_service._normalize_phone(request.phone_number)
    is_valid = await otp_service.verify_otp(phone_number, request.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP code",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    # Enable bypass for user creation/lookup after OTP verification
    await set_rls_bypass(db)
    user, is_new = await user_service.get_or_create_user_by_phone(phone_number)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": is_new or not user.full_name,
    }


# ─── Google SSO ────────────────────────────────────────────────────────────────


class GoogleAuthRequest(BaseModel):
    id_token: str


@router.post("/google", response_model=Token)
async def google_sso(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a Google ID token issued by the Google Sign-In SDK.
    Creates the user account on first sign-in, then returns a KukuFiti JWT.

    Requires GOOGLE_CLIENT_ID set in the environment.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google SSO is not configured on this server.",
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.id_token},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token.",
        )

    claims = resp.json()

    # Audience check — the token must be issued for our app
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token audience mismatch.",
        )

    email: str | None = claims.get("email")
    full_name: str | None = claims.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email address.",
        )

    service = UserService(db)
    # Enable bypass for SSO user creation/lookup
    await set_rls_bypass(db)
    user, is_new = await service.get_or_create_user_by_email(
        email=email,
        full_name=full_name,
        sso_provider="google",
    )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": is_new,
    }


# ─── Apple SSO ─────────────────────────────────────────────────────────────────


class AppleAuthRequest(BaseModel):
    identity_token: str
    full_name: str | None = None


@router.post("/apple", response_model=Token)
async def apple_sso(
    payload: AppleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify an Apple identity token issued by Sign in with Apple.
    Creates the user account on first sign-in, then returns a KukuFiti JWT.

    Requires APPLE_CLIENT_ID set in the environment.
    """
    if not settings.APPLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple SSO is not configured on this server.",
        )

    # Fetch Apple's public JWKS
    async with httpx.AsyncClient() as client:
        jwks_resp = await client.get("https://appleid.apple.com/auth/keys")

    if jwks_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not fetch Apple public keys.",
        )

    # Decode the JWT header to find the matching key id
    try:
        header_segment = payload.identity_token.split(".")[0]
        # Pad base64 string
        padded = header_segment + "=" * (4 - len(header_segment) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        kid = header.get("kid")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Apple identity token.",
        )

    jwks = jwks_resp.json().get("keys", [])
    matching_key = next((k for k in jwks if k.get("kid") == kid), None)

    if not matching_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple public key not found for this token.",
        )

    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric.rsa import \
            RSAPublicNumbers
        from jose import JWTError
        from jose import jwt as jose_jwt

        def _base64url_to_int(val: str) -> int:
            padded = val + "=" * (4 - len(val) % 4)
            data = base64.urlsafe_b64decode(padded)
            return int.from_bytes(data, "big")

        public_numbers = RSAPublicNumbers(
            e=_base64url_to_int(matching_key["e"]),
            n=_base64url_to_int(matching_key["n"]),
        )
        public_key = public_numbers.public_key(default_backend())

        claims = jose_jwt.decode(
            payload.identity_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
            issuer="https://appleid.apple.com",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Apple identity token verification failed: {exc}",
        )

    email: str | None = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple account has no email address.",
        )

    service = UserService(db)
    # Enable bypass for SSO user creation/lookup
    await set_rls_bypass(db)
    user, is_new = await service.get_or_create_user_by_email(
        email=email,
        full_name=payload.full_name,
        sso_provider="apple",
    )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": is_new,
    }
