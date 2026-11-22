from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "url_shortener",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-links-every-minute": {
        "task": "app.workers.tasks.cleanup_expired_links_task",
        "schedule": 60.0,
    },
}
