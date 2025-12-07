from sqlalchemy import Column, String, Date, DECIMAL, CheckConstraint, Integer
from app.db.base import Base, TimestampMixin, UUIDMixin

class MarketPrice(Base, UUIDMixin, TimestampMixin):
    """
    Records market price data for intelligence/comparison.
    """
    __tablename__ = "market_prices"

    price_date = Column(Date, nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    town = Column(String(100))
    
    price_per_kg = Column(DECIMAL(10, 2), nullable=False)
    price_per_bird = Column(DECIMAL(10, 2))
    
    source = Column(String(255), doc="Source of data (e.g., 'Ministry of Ag', 'Local Market')")
    notes = Column(String(255))

    __table_args__ = (
        CheckConstraint("price_per_kg > 0", name="positive_price_per_kg"),
    )
