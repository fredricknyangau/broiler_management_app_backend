from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class ApiKey(Base, UUIDMixin, TimestampMixin):
    """
    API access keys generated for Enterprise API access nodes.
    """

    __tablename__ = "api_keys"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(
        String(255), nullable=False, doc="Label for the Key e.g. ERP Integration"
    )
    key_prefix = Column(String(20), nullable=False, doc="e.g. kf_live_")
    key_hash = Column(String(255), nullable=False, doc="Hashed secret for validation")
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ApiKey(name='{self.name}', prefix='{self.key_prefix}')>"
