from app.workers.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def test_task(message: str):
    """Simple test task"""
    logger.info(f"Test task received: {message}")
    return f"Processed: {message}"


from app.db.session import SessionLocal
from app.services.alert_service import AlertService
from app.db.models.flock import Flock
from app.db.models.daily_check import DailyCheck
from app.db.models.events import MortalityEvent
from app.schemas.daily_check import EventType

@celery_app.task
def evaluate_alerts_task(flock_id: str, check_date: str):
    """
    Evaluates daily data to generate alerts.
    """
    logger.info(f"Evaluating alerts for flock {flock_id} on {check_date}")
    
    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        
        # 1. Fetch Flock
        flock = db.query(Flock).filter(Flock.id == flock_id).first()
        if not flock:
            logger.error(f"Flock {flock_id} not found during alert eval")
            return
            
        # 2. Fetch Mortality for the date
        # We need to find the daily check or events directly
        # Assuming we can find events by date and flock via join or direct query
        # Ideally we queried the DailyCheck first, but let's look for MortalityEvents directly for simplicity if possible,
        # or find the DailyCheck.
        
        daily_check = db.query(DailyCheck).filter(
            DailyCheck.flock_id == flock_id,
            DailyCheck.check_date == check_date
        ).first()
        
        if daily_check:
             # Sum mortality events linked to this check
             mortality_count = 0
             for event in daily_check.events:
                 if event.event_type == EventType.MORTALITY:
                     mortality_count += (event.count or 0)
            
             if mortality_count > 0:
                 alert_service.check_mortality(flock.id, mortality_count, flock.initial_count)
                 
    except Exception as e:
        logger.error(f"Error evaluating alerts: {e}")
    finally:
        db.close()
    
    return {"status": "evaluated", "flock_id": flock_id}


@celery_app.task
def refresh_flock_stats_task():
    """Placeholder for refreshing flock stats"""
    logger.info("Refreshing flock stats")
    # TODO: Add actual stats refresh logic
    return {"status": "success"}
