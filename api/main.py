"""FastAPI entry points for the market research agent.

Endpoints:
    POST /research                  — enqueue a background research job.
    GET  /research/{task_id}        — poll job status / result.

Run with::

    uvicorn api.main:app --reload

Requires a running Redis and a Celery worker::

    celery -A worker.research_task worker --loglevel=info
"""

from typing import Any

from celery.result import AsyncResult
from fastapi import FastAPI
from pydantic import BaseModel, Field

from tasks import validate_input
from worker.celery_app import celery_app
from worker.research_task import run_research_task

app = FastAPI(
    title="Market Research Agent API",
    description="Enqueue and poll async market research jobs.",
    version="1.0.0",
)


class ResearchRequest(BaseModel):
    """Body for starting a research job."""

    product_idea: str = Field(min_length=1, description="The product idea to research.")
    mode: str = Field(default="deep", pattern="^(quick|deep)$")


@app.get("/")
def root() -> dict[str, str]:
    """Basic liveness probe."""
    return {"status": "ok", "service": "market-research-agent"}


@app.post("/research")
def start_research(req: ResearchRequest) -> dict[str, str]:
    """Validate input, enqueue the job, and return its Celery task id."""
    validate_input(req.product_idea)
    task = run_research_task.delay(req.product_idea, req.mode)
    return {"task_id": task.id}


@app.get("/research/{task_id}")
def get_research(task_id: str) -> dict[str, Any]:
    """Return the current status and (when ready) the result for a job."""
    result: AsyncResult = AsyncResult(task_id, app=celery_app)
    if result.failed():
        return {
            "status": result.status,
            "task_id": task_id,
            "result": None,
            "error": str(result.result),
        }
    return {
        "status": result.status,
        "task_id": task_id,
        "result": result.result,
    }