from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.events import MortalityEvent, FeedConsumptionEvent, VaccinationEvent, WeightMeasurementEvent
from app.db.models.finance import Expenditure, Sale
from app.db.models.inventory import InventoryItem
from app.db.models.biosecurity import BiosecurityCheck
from app.db.models.health import VetConsultation
from app.db.models.market import MarketPrice
from app.db.models.alert import Alert

from app.schemas.user import UserResponse
from app.schemas.flock import FlockResponse
# Import other schemas... Assuming they exist in respective schema files or defining generic ones?
# To avoid circular imports or complex schema setups, I will define a comprehensive SyncResponse here relying on existing schemas if possible.
# But I might not have Response schemas for all. I'll check.
from app.schemas.daily_check import (
    MortalityEventResponse, 
    FeedConsumptionEventResponse, 
    VaccinationEventResponse, 
    WeightMeasurementEventResponse
)
from app.schemas.finance import ExpenditureResponse, SaleResponse
from app.schemas.inventory import InventoryItemResponse
from app.schemas.biosecurity import BiosecurityCheckResponse
from app.schemas.health import VetConsultationResponse
from app.schemas.market import MarketPriceResponse
from app.schemas.alert import AlertResponse


router = APIRouter()

# --- Schemas --- (If not available elsewhere, redefine or import)
# Ideally I should verify imports first. 

class EventsCollection(BaseModel):
    mortality: List[MortalityEventResponse]
    feed: List[FeedConsumptionEventResponse]
    vaccination: List[VaccinationEventResponse]
    weight: List[WeightMeasurementEventResponse]

class FinanceCollection(BaseModel):
    expenditures: List[ExpenditureResponse]
    sales: List[SaleResponse]

class HealthCollection(BaseModel):
    consultations: List[VetConsultationResponse]

class MarketCollection(BaseModel):
    prices: List[MarketPriceResponse]

class SyncResponse(BaseModel):
    user: UserResponse
    flocks: List[FlockResponse]
    events: EventsCollection
    finance: FinanceCollection
    inventory: List[InventoryItemResponse]
    biosecurity: List[BiosecurityCheckResponse]
    health: HealthCollection
    market: MarketCollection
    alerts: List[AlertResponse]


@router.get("/sync", response_model=SyncResponse)
def sync_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all user data in a single request.
    Optimized for initial load and sync.
    """
    
    # 1. Flocks
    flocks = db.query(Flock).filter(Flock.farmer_id == current_user.id).all()
    # Optimization: Only fetch events for ACTIVE flocks to speed up sync
    # Historical data for closed batches won't be loaded in full detail on sync
    active_flock_ids = [f.id for f in flocks if f.status == 'active']
    
    # 2. Events (linked to ACTIVE flocks only)
    mortality = db.query(MortalityEvent).filter(MortalityEvent.flock_id.in_(active_flock_ids)).all()
    feed = db.query(FeedConsumptionEvent).filter(FeedConsumptionEvent.flock_id.in_(active_flock_ids)).all()
    vaccination = db.query(VaccinationEvent).filter(VaccinationEvent.flock_id.in_(active_flock_ids)).all()
    weight = db.query(WeightMeasurementEvent).filter(WeightMeasurementEvent.flock_id.in_(active_flock_ids)).all()
    
    # 3. Finance
    expenditures = db.query(Expenditure).filter(Expenditure.farmer_id == current_user.id).all()
    sales = db.query(Sale).filter(Sale.farmer_id == current_user.id).all()
    
    # 4. Inventory & Biosecurity
    inventory = db.query(InventoryItem).filter(InventoryItem.farmer_id == current_user.id).all()
    biosecurity = db.query(BiosecurityCheck).filter(BiosecurityCheck.farmer_id == current_user.id).all()
    
    # 5. Health & Market
    vet_consultations = db.query(VetConsultation).filter(VetConsultation.farmer_id == current_user.id).all()
    
    # Market prices (last 90 days, global)
    ninety_days_ago = datetime.utcnow().date() - timedelta(days=90)
    market_prices = db.query(MarketPrice).filter(MarketPrice.price_date >= ninety_days_ago).all()
    # market_prices = []
    
    # 6. Alerts
    alerts = db.query(Alert).filter(Alert.flock_id.in_(active_flock_ids)).all()
    # alerts = []
    
    return {
        "user": current_user,
        "flocks": flocks,
        "events": {
            "mortality": mortality,
            "feed": feed,
            "vaccination": vaccination,
            "weight": weight
        },
        "finance": {
            "expenditures": expenditures,
            "sales": sales
        },
        "inventory": inventory,
        "biosecurity": biosecurity,
        "health": {
            "consultations": vet_consultations
        },
        "market": {
            "prices": market_prices
        },
        "alerts": alerts
    }
