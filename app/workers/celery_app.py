from celery import Celery
from app.config import settings

celery_app = Celery(
    "broiler_farm_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.tasks.evaluate_alerts_task": {"queue": "alerts"},
    "app.workers.tasks.refresh_flock_stats_task": {"queue": "stats"},
    "app.workers.tasks.send_notification_task": {"queue": "notifications"},
}