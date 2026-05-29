from celery import Celery

from src.config.logging import configure_logging
from src.config.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)

celery_app = Celery(
    "sshop_price_tracker",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["src.infrastructure.tasks.product_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sync-samsung-products": {
            "task": "src.infrastructure.tasks.product_tasks.sync_samsung_products",
            "schedule": settings.sync_interval_seconds,
        }
    },
)
