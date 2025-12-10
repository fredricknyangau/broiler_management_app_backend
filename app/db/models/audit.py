from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base, UUIDMixin

class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False, doc="Action performed (e.g., CREATE_USER, DELETED_FLOCK)")
    resource_type = Column(String(100), nullable=True, doc="Resource type (e.g., User, Flock)")
    resource_id = Column(String(36), nullable=True, doc="ID of the resource affected")
    details = Column(JSON, nullable=True, doc="Additional details or diff")
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user='{self.user_id}', time='{self.timestamp}')>"
