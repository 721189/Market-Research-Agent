import os
from celery import Celery
from backend.app.config import settings

celery_app = Celery(
    "marketai_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.app.workers.research_worker",
        "backend.app.workers.analysis_worker",
        "backend.app.workers.pdf_worker",
    ]
)

# 3.2 Queue routing design
celery_app.conf.task_routes = {
    "backend.app.workers.research_worker.execute_research_job": {"queue": "research.deep"},
    "backend.app.workers.research_worker.execute_quick_research_job": {"queue": "research.quick"},
    "backend.app.workers.analysis_worker.analyze_evidence_task": {"queue": "analysis"},
    "backend.app.workers.pdf_worker.generate_pdf_report_task": {"queue": "reports"},
}

# 26. Queue reliability & fault tolerance settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True, # Phase 26: acknowledge after completion to prevent job loss
    task_reject_on_worker_lost=True,
    task_time_limit=3600, # 1 hour max
    worker_prefetch_multiplier=1, # Fair dispatch
)
