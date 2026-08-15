"""Celery application factory.

Broker/backend URLs come from the environment with localhost defaults so
the same module runs both locally and under docker-compose.
"""

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "market_research",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Silence Celery 5.x startup warning and keep the worker resilient if
# Redis is briefly unavailable at boot.
celery_app.conf.broker_connection_retry_on_startup = True

# Auto-discover tasks defined in the worker package when ``-A worker`` is used.
celery_app.autodiscover_tasks(["worker"])