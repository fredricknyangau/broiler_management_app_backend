from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class ScheduledTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scheduled_tasks"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flock_id = Column(
        UUID(as_uuid=True),
        ForeignKey("flocks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    category = Column(String(100), default="general", nullable=False)

    def __repr__(self):
        return f"<ScheduledTask(title='{self.title}', status='{self.status}')>"
