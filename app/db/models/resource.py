from sqlalchemy import Column, String, Text
from app.db.base import Base, TimestampMixin, UUIDMixin

class Resource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resources"

    title = Column(String(255), nullable=False, doc="Title of the resource/guide")
    description = Column(String(500), nullable=True, doc="Short description")
    content = Column(Text, nullable=False, doc="Main content/body")
    category = Column(String(100), default="general", nullable=False, index=True)
    icon = Column(String(100), nullable=True, doc="Lucide icon name")

    def __repr__(self):
        return f"<Resource(title='{self.title}', category='{self.category}')>"
