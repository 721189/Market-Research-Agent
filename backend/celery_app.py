import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "marketai_worker",
    broker=redis_url,
    backend=redis_url,
    include=["backend.tasks"]
)

# Route tasks to distinct queues to prevent starvation
celery_app.conf.task_routes = {
    "backend.tasks.execute_research_job": {"queue": "research.deep"},
    "backend.tasks.analyze_evidence": {"queue": "analysis"},
    "backend.tasks.generate_pdf_report": {"queue": "reports"},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
)
