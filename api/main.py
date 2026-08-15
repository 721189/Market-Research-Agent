"""FastAPI entry points for the market research agent.

Endpoints:
    POST /research                  — enqueue a background research job.
    GET  /research/{task_id}        — poll job status / result.

Run with::

    uvicorn api.main:app --reload

Requires a running Redis and a Celery worker::

    celery -A worker.research_task worker --loglevel=info

Phase 3 hardening: per-client rate limiting (slowapi), PII redaction before
any data is persisted, and append-only CSV audit logging.
"""

from typing import Any

from celery.result import AsyncResult
from fastapi import FastAPI, Header, Request
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from audit import log_request
from pii_redactor import redact_pii
from rate_limiter import limiter
from tasks import validate_input
from worker.celery_app import celery_app
from worker.research_task import run_research_task

app = FastAPI(
    title="Market Research Agent API",
    description="Enqueue and poll async market research jobs.",
    version="1.1.0",  # Phase 3: security & compliance
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class ResearchRequest(BaseModel):
    """Body for starting a research job."""

    product_idea: str = Field(min_length=1, description="The product idea to research.")
    mode: str = Field(default="deep", pattern="^(quick|deep|batch)$")


@app.get("/")
def root() -> dict[str, str]:
    """Basic liveness probe."""
    return {"status": "ok", "service": "market-research-agent"}


@app.post("/research")
@limiter.limit("100/day")
def start_research(
    request: Request,
    req: ResearchRequest,
    user_id: str = Header(default="anonymous", alias="X-User-ID"),
) -> dict[str, str]:
    """Validate input, enqueue the job, and return its Celery task id.

    Rate-limited to 100 requests per day per client IP. Logs an audit row
    with PII redacted before it reaches the CSV.
    """
    validate_input(req.product_idea)
    task = run_research_task.delay(req.product_idea, req.mode)
    # Only redacted values are persisted to the audit trail.
    log_request(
        user_id=redact_pii(user_id),
        product=redact_pii(req.product_idea),
        task_id=task.id,
    )
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