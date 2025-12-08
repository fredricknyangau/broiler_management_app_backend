from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date, timedelta
from app.api.deps import get_db, get_current_user, set_tenant_context
from app.db.models.user import User
from app.db.models.flock import Flock
from app.db.models.daily_check import DailyCheck
from app.schemas.daily_check import DailyCheckCreate, DailyCheckResponse, EventType
from app.services.daily_check_service import DailyCheckService
from app.workers.tasks import evaluate_alerts_task

router = APIRouter()


@router.post("/daily-checks", response_model=DailyCheckResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_check(
    check_data: DailyCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit daily check with observations and events (batch endpoint).
    
    This endpoint handles:
    - Recording daily observations (temperature, behavior, etc.)
    - Processing multiple events (mortality, feed, vaccination, weight)
    - Idempotency via event_id to prevent duplicates
    - Queuing alert evaluation for background processing
    """
    # Set tenant context for RLS
    set_tenant_context(db, current_user)
    
    # Verify flock ownership
    flock = db.query(Flock).filter(
        Flock.id == check_data.flock_id,
        Flock.farmer_id == current_user.id
    ).first()
    if not flock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flock {check_data.flock_id} not found"
        )
    
    # Create daily check service
    service = DailyCheckService(db)
    
    try:
        # Process the check and events
        result = service.process_daily_check(
            flock_id=check_data.flock_id,
            check_date=check_data.check_date,
            observations={
                "temperature_celsius": check_data.temperature_celsius,
                "humidity_percent": check_data.humidity_percent,
                "chick_behavior": check_data.chick_behavior,
                "litter_condition": check_data.litter_condition,
                "feed_level": check_data.feed_level,
                "water_level": check_data.water_level,
                "general_notes": check_data.general_notes,
                "check_time": check_data.check_time,
                "recorded_by": current_user.id
            },
            events=check_data.events
        )
        
        # Queue alert evaluation (async background task)
        evaluate_alerts_task.delay(
            flock_id=str(check_data.flock_id),
            check_date=str(check_data.check_date)
        )
        
        return DailyCheckResponse(
            check_id=result["check_id"],
            flock_id=check_data.flock_id,
            check_date=check_data.check_date,
            events_processed=result["events_processed"],
            alerts_triggered=[]  # Alerts are processed asynchronously
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/daily-checks/{flock_id}")
async def get_daily_checks(
    flock_id: UUID,
    start_date: date = None,
    end_date: date = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily checks for a flock with optional date range.
    
    - Defaults to last 30 days if no dates provided.
    - Returns list ordered by date descending.
    """
    set_tenant_context(db, current_user)
    
    # Verify flock ownership
    flock = db.query(Flock).filter(
        Flock.id == flock_id,
        Flock.farmer_id == current_user.id
    ).first()
    if not flock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flock {flock_id} not found"
        )
    
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    checks = db.query(DailyCheck).filter(
        DailyCheck.flock_id == flock_id,
        DailyCheck.check_date >= start_date,
        DailyCheck.check_date <= end_date
    ).order_by(DailyCheck.check_date.desc()).limit(limit).all()
    
    return checks


@router.get("/daily-checks/{flock_id}/{check_date}")
async def get_daily_check_by_date(
    flock_id: UUID,
    check_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific daily check by date.
    
    - Returns 404 if no check exists for that date.
    """
    set_tenant_context(db, current_user)
    
    # Verify flock ownership
    flock = db.query(Flock).filter(
        Flock.id == flock_id,
        Flock.farmer_id == current_user.id
    ).first()
    if not flock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flock {flock_id} not found"
        )
    
    check = db.query(DailyCheck).filter(
        DailyCheck.flock_id == flock_id,
        DailyCheck.check_date == check_date
    ).first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No check found for {check_date}"
        )
    
    return check