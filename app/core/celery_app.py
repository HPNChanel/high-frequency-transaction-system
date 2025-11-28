"""Celery application instance for asynchronous task processing."""

from celery import Celery
from app.core.config import get_settings

# Load settings
settings = get_settings()

# Create Celery instance with unique application name
celery_app = Celery(
    "hfts_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    # Serialization settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone settings
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking and execution settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    result_expires=3600,  # Results expire after 1 hour
)
