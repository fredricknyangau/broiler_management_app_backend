from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a raw password against its bcrypt hash.
    
    Args:
        plain_password (str): Raw password input.
        hashed_password (str): Stored bcrypt hash.
        
    Returns:
        bool: True if password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash for a password.
    
    Args:
        password (str): Raw password to hash.
        
    Returns:
        str: Bcrypt hash string.
    """
    # Ensure password is not longer than 72 bytes
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data (dict): Payload data (e.g., user ID).
        expires_delta (timedelta, optional): Custom expiration duration.
        
    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# Constants for use in app/api/deps.py
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
