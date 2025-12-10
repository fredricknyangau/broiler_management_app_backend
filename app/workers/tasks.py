from app.workers.celery_app import celery_app
import logging
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


@celery_app.task
def test_task(message: str):
    """Simple test task"""
    logger.info(f"Test task received: {message}")
    return f"Processed: {message}"


from app.db.session import AsyncSessionLocal
from app.services.alert_service import AlertService
from app.db.models.flock import Flock
from app.db.models.daily_check import DailyCheck
from app.db.models.events import MortalityEvent
from app.schemas.daily_check import EventType

async def evaluate_alerts_async(flock_id: str, check_date: str):
    async with AsyncSessionLocal() as db:
        try:
            alert_service = AlertService(db)
            
            # 1. Fetch Flock
            result = await db.execute(select(Flock).filter(Flock.id == flock_id))
            flock = result.scalars().first()
            if not flock:
                logger.error(f"Flock {flock_id} not found during alert eval")
                return
                
            # 2. Fetch DailyCheck
            result = await db.execute(
                select(DailyCheck)
                .options(selectinload(DailyCheck.events))
                .filter(
                    DailyCheck.flock_id == flock_id,
                    DailyCheck.check_date == check_date
                )
            )
            daily_check = result.scalars().first()
            
            if daily_check:
                 # Sum mortality events linked to this check
                 mortality_count = 0
                 for event in daily_check.events:
                     if event.event_type == EventType.MORTALITY:
                         mortality_count += (event.count or 0)
                
                 if mortality_count > 0:
                     await alert_service.check_mortality(flock.id, mortality_count, flock.initial_count)
                     
        except Exception as e:
            logger.error(f"Error evaluating alerts: {e}")

@celery_app.task
def evaluate_alerts_task(flock_id: str, check_date: str):
    """
    Evaluates daily data to generate alerts.
    """
    logger.info(f"Evaluating alerts for flock {flock_id} on {check_date}")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(evaluate_alerts_async(flock_id, check_date))
    
    return {"status": "evaluated", "flock_id": flock_id}


@celery_app.task
def refresh_flock_stats_task():
    """Placeholder for refreshing flock stats"""
    logger.info("Refreshing flock stats")
    # TODO: Add actual stats refresh logic
    return {"status": "success"}
