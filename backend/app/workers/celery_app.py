from celery import Celery

from app.config import get_settings

_settings = get_settings()
celery_app = Celery(
    "disprot",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.task_default_queue = "disprot"
celery_app.conf.task_track_started = True
celery_app.autodiscover_tasks(["app.workers"])
