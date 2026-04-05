from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, UUIDMixin
import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    VIEWER = "VIEWER"
    FARMER = "FARMER"


class User(Base, UUIDMixin, TimestampMixin):
    """
    Represents a registered user (farmer) in the system.
    
    Users own flocks and data. Authentication is handled via email/password.
    """
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=True, index=True, doc="User's unique email address")
    hashed_password = Column(String(255), nullable=True, doc="Bcrypt hashed password")
    full_name = Column(String(255), doc="User's full display name")
    phone_number = Column(String(20), doc="Contact phone number")
    location = Column(String(255), doc="Farm location or user's address")
    county = Column(String(100), nullable=True, index=True, doc="Kenyan County for regional benchmarking")
    is_active = Column(Boolean, default=True, nullable=False, doc="Designates whether this user should be treated as active")
    is_superuser = Column(Boolean, default=False, nullable=False, doc="Designates whether this user has admin privileges")
    preferences = Column(JSON, default={}, nullable=True, doc="User's personalized settings and preferences")

    # Relationships
    flocks = relationship("Flock", back_populates="farmer", cascade="all, delete-orphan")
    role = Column(String(50), default="FARMER", nullable=False, server_default="FARMER", doc="User's role (ADMIN, MANAGER, VIEWER, FARMER)")

    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.full_name}', role='{self.role}')>"