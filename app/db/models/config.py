from sqlalchemy import Column, String, Text, Boolean
from app.db.base import Base, TimestampMixin, UUIDMixin

class SystemConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_config"

    key = Column(String(255), unique=True, index=True, nullable=False, doc="Configuration key")
    value = Column(Text, nullable=True, doc="Configuration value")
    category = Column(String(100), default="general", nullable=False, doc="Category (security, general, notifications)")
    is_encrypted = Column(Boolean, default=False, doc="Whether the value is encrypted")

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', category='{self.category}')>"
