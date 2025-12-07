from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.core.security import get_password_hash, verify_password


class UserService:
    """Service for user operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, email: str, password: str, **kwargs) -> User:
        """Create a new user"""
        # Check if user already exists
        existing = self.get_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")
        
        # Create user
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            **kwargs
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except Exception as e:
            self.db.rollback()
            # If it's an integrity error, we might want to be specific, 
            # but for now, generic catching or re-raising as ValueError helps the API layer
            if "unique constraint" in str(e).lower():
                 raise ValueError("User with this email or phone number already exists")
            raise e
        
        return user
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.get_by_email(email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user details"""
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
