"""Celery tasks for background processing."""

import os

from celery import Celery

from openscience.core.session import ScienceSession

# Initialize Celery
celery_app = Celery(
    "openscience",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(bind=True, name="openscience.analyze_data")
def analyze_data_task(self, file_path, task_description, specialist=None):
    """Background task for data analysis."""
    try:
        session = ScienceSession()
        session.load_data(file_path)
        result = session.analyze(task_description, specialist=specialist)
        return {"status": "success", "result": str(result), "task_id": self.request.id}
    except Exception as e:
        return {"status": "error", "error": str(e), "task_id": self.request.id}


@celery_app.task(name="openscience.health_check")
def health_check():
    """Health check task for worker monitoring."""
    return {"status": "healthy"}
