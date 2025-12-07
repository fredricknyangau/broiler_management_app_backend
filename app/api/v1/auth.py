from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.api.deps import get_db, get_current_user
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.user_service import UserService
from app.core.security import create_access_token
from app.config import settings
from app.db.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new farmer account.
    
    - **email**: Valid email address (will be used for login)
    - **password**: Minimum 8 characters
    - **full_name**: Farmer's full name
    - **phone_number**: Contact number (e.g., +254712345678)
    - **location**: Farm location
    """
    service = UserService(db)
    
    try:
        user = service.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            location=user_data.location
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
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
    
    # Authenticate user
    user = service.authenticate(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile.
    
    Requires authentication (JWT token in Authorization header).
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_profile(
    full_name: str = None,
    phone_number: str = None,
    location: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    Requires authentication.
    """
    service = UserService(db)
    
    updated_user = service.update_user(
        user_id=str(current_user.id),
        full_name=full_name,
        phone_number=phone_number,
        location=location
    )
    
    return updated_user
