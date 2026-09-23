"""Celery application.

Separate process tree from both FastAPI and Frappe. A GPU worker that dies
on an out-of-memory error takes down neither the ingestion API nor Frappe's
transactional queues, which is the point of the split.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("screening", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,            # redeliver if a worker dies mid-parse
    worker_prefetch_multiplier=1,   # long tasks: do not hoard the queue
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    task_reject_on_worker_lost=True,
)
