from sqlalchemy import Column, String, JSON
from app.db.base import Base, TimestampMixin, UUIDMixin

class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, index=True, nullable=False, doc="Role name (ADMIN, MANAGER, etc.)")
    description = Column(String(255), nullable=True, doc="Role description")
    permissions = Column(JSON, default={}, nullable=False, doc="JSON dict of permissions e.g. {'manage_users': true}")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
