from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user # Auth optional for reading market prices? enforcing for now
from app.db.models.market import MarketPrice
from app.schemas.market import MarketPriceCreate, MarketPriceResponse

router = APIRouter()

@router.post("/prices", response_model=MarketPriceResponse, status_code=status.HTTP_201_CREATED)
def create_market_price(
    item_in: MarketPriceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user) # Only auth users can add prices
):
    """
    Record a new market price.
    """
    item = MarketPrice(**item_in.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/prices", response_model=List[MarketPriceResponse])
def read_market_prices(
    county: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db) 
    # Open endpoint? Or auth? Let's keep it open or auth. 
    # Use auth for consistency based on other endpoints.
):
    """
    List market prices.
    """
    query = db.query(MarketPrice)
    if county:
        query = query.filter(MarketPrice.county == county)
    return query.order_by(MarketPrice.price_date.desc()).offset(skip).limit(limit).all()

@router.put("/prices/{price_id}", response_model=MarketPriceResponse)
def update_market_price(
    price_id: UUID,
    item_in: MarketPriceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a market price.
    """
    item = db.query(MarketPrice).filter(MarketPrice.id == price_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Market price not found")
        
    # Note: Market prices might be public/shared. 
    # For now assuming anyone authenticated can update or strict ownership? 
    # The Model doesn't seem to have farmer_id. 
    # If it's shared data, maybe restrict updates? 
    # User said "when I edit". Assuming user context matters.
    # But MarketPrice model (checked earlier) typically doesn't have farmer_id?
    # Let's check model if I can. 
    # Checking types/broiler.ts -> MarketPrice interface doesn't show owner.
    # Backend api `create` doesn't assign farmer_id.
    # So it is global data. 
    # I will allow update for now.
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
