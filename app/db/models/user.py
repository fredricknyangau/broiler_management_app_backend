from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """
    Represents a registered user (farmer) in the system.
    
    Users own flocks and data. Authentication is handled via email/password.
    """
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True, doc="User's unique email address")
    hashed_password = Column(String(255), nullable=False, doc="Bcrypt hashed password")
    full_name = Column(String(255), doc="User's full display name")
    phone_number = Column(String(20), doc="Contact phone number")
    location = Column(String(255), doc="Farm location or user's address")
    is_active = Column(Boolean, default=True, nullable=False, doc="Designates whether this user should be treated as active")
    is_superuser = Column(Boolean, default=False, nullable=False, doc="Designates whether this user has admin privileges")
    preferences = Column(JSON, default={}, nullable=True, doc="User's personalized settings and preferences")

    # Relationships
    flocks = relationship("Flock", back_populates="farmer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.full_name}')>"