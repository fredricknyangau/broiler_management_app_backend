from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt
from uuid import UUID

from app.db.session import get_db
from app.db.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate JWT token, return current user.
    Usage: current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def set_tenant_context(db: Session, user: User):
    """
    Set PostgreSQL session variable for RLS.
    Call this after getting current_user in protected routes.
    """
    db.execute(
        text(f"SET LOCAL app.current_user_id = '{str(user.id)}'")
    )
    db.commit()


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if current user is a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
