from app.workers.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def test_task(message: str):
    """Simple test task"""
    logger.info(f"Test task received: {message}")
    return f"Processed: {message}"


@celery_app.task
def evaluate_alerts_task(flock_id: str, check_date: str):
    """
    Placeholder for alert evaluation.
    Will be implemented once models are created.
    """
    logger.info(f"Evaluating alerts for flock {flock_id} on {check_date}")
    # TODO: Add actual alert evaluation logic
    return {
        "flock_id": flock_id,
        "check_date": check_date,
        "status": "evaluated"
    }


@celery_app.task
def refresh_flock_stats_task():
    """Placeholder for refreshing flock stats"""
    logger.info("Refreshing flock stats")
    # TODO: Add actual stats refresh logic
    return {"status": "success"}
