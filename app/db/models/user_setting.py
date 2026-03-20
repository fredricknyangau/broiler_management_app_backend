from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampMixin, UUIDMixin

class UserSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True, doc="Setting key (e.g., theme)")
    value = Column(Text, nullable=True, doc="Setting value")
    category = Column(String(100), default="general", nullable=False)

    def __repr__(self):
        return f"<UserSetting(user_id='{self.user_id}', key='{self.key}')>"
