from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "trendsee",
    broker=settings.effective_celery_broker,
    backend=settings.effective_celery_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    imports=("app.tasks.generation_tasks",),
)
