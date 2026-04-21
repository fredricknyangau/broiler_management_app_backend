import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def test_task(message: str):
    """Simple test task"""
    logger.info(f"Test task received: {message}")
    return f"Processed: {message}"


from app.db.models.daily_check import DailyCheck
from app.db.models.events import MortalityEvent
from app.db.models.flock import Flock
from app.db.session import AsyncSessionLocal
from app.schemas.daily_check import EventType
from app.services.alert_service import AlertService


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
                    DailyCheck.flock_id == flock_id, DailyCheck.check_date == check_date
                )
            )
            daily_check = result.scalars().first()

            if daily_check:
                # Sum mortality events linked to this check
                mortality_count = 0
                for event in daily_check.events:
                    if event.event_type == EventType.MORTALITY:
                        mortality_count += event.count or 0

                if mortality_count > 0:
                    await alert_service.check_mortality(
                        flock.id, mortality_count, flock.initial_count
                    )

        except Exception as e:
            logger.error(f"Error evaluating alerts: {e}")


@celery_app.task
def evaluate_alerts_task(flock_id: str, check_date: str):
    """
    Evaluates daily data to generate alerts.

    Uses ``asyncio.run()`` which always creates a fresh event loop per invocation.
    This is the correct pattern for bridging sync Celery workers to async SQLAlchemy.
    ``asyncio.get_event_loop()`` is deprecated in Python 3.10+ and will fail inside
    Celery thread pools where no running loop exists.
    """
    logger.info(f"Evaluating alerts for flock {flock_id} on {check_date}")
    asyncio.run(evaluate_alerts_async(flock_id, check_date))
    return {"status": "evaluated", "flock_id": flock_id}


from app.db.models.events import MortalityEvent
from app.db.models.finance import Sale


async def _refresh_flock_stats_async() -> dict:
    """
    Recompute and log a summary of current bird counts, mortality, and revenue
    for all active flocks across the system. Designed to run periodically (e.g. hourly)
    as a health-check snapshot to catch data drift and alert generation delays.
    """
    from sqlalchemy import func

    from app.db.models.flock import Flock as FlockModel

    async with AsyncSessionLocal() as db:
        try:
            # Total active flocks
            active_res = await db.execute(
                select(func.count())
                .select_from(FlockModel)
                .filter(FlockModel.status == "active")
            )
            active_count = active_res.scalar_one() or 0

            # Total initial birds in active flocks
            initial_res = await db.execute(
                select(func.sum(FlockModel.initial_count)).filter(
                    FlockModel.status == "active"
                )
            )
            total_initial = initial_res.scalar() or 0

            # Total recorded mortalities across active flocks
            mort_res = await db.execute(
                select(func.sum(MortalityEvent.count))
                .join(FlockModel, FlockModel.id == MortalityEvent.flock_id)
                .filter(FlockModel.status == "active")
            )
            total_mort = mort_res.scalar() or 0

            # Total birds sold from active flocks
            sales_res = await db.execute(
                select(func.sum(Sale.quantity))
                .join(FlockModel, FlockModel.id == Sale.flock_id)
                .filter(FlockModel.status == "active")
            )
            total_sold = sales_res.scalar() or 0

            current_birds = max(0, total_initial - total_mort - total_sold)
            mortality_rate = (
                round((total_mort / total_initial * 100), 2) if total_initial > 0 else 0
            )

            summary = {
                "active_flocks": active_count,
                "total_initial_birds": total_initial,
                "total_mortalities": total_mort,
                "total_sold": total_sold,
                "current_birds": current_birds,
                "mortality_rate_pct": mortality_rate,
            }
            logger.info(f"Flock stats refreshed: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error during flock stats refresh: {e}")
            return {}


@celery_app.task
def refresh_flock_stats_task():
    """
    Periodically recomputes active flock stats (bird count, mortality rate, sales)
    across all farmers and logs a system-wide snapshot.

    Follows the same asyncio.run() bridging pattern as evaluate_alerts_task:
    Celery workers are synchronous; asyncio.run() spawns a fresh event loop
    per invocation so we can safely use AsyncSession inside a sync task.
    """
    logger.info("Starting flock stats refresh")
    result = asyncio.run(_refresh_flock_stats_async())
    return {"status": "success", **result}
