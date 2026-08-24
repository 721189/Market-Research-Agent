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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from audit import log_request
from pdf_export import generate_pdf
from pii_redactor import redact_pii
from rate_limiter import limiter
from tasks import FinancialAnalysis, validate_input
from worker.celery_app import celery_app
from worker.research_task import run_research_task

app = FastAPI(
    title="Market Research Agent API",
    description="Enqueue and poll async market research jobs.",
    version="1.1.0",  # Phase 3: security & compliance
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow the Next.js frontend (dev on :3000) to reach this API and read the
# SSE stream / download the PDF. Restrict to local origins by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    # While a task is RETRYing, ``result.result`` holds the raised exception
    # instance (e.g. ValueError) which is not JSON-serializable — surface it
    # as an error string instead of letting FastAPI blow up with a 500.
    payload = result.result
    if not isinstance(payload, dict):
        error_text = str(payload) if payload is not None else None
        return {
            "status": result.status,
            "task_id": task_id,
            "result": None,
            "error": error_text,
        }
    return {
        "status": result.status,
        "task_id": task_id,
        "result": payload,
    }


@app.get("/research/{task_id}/pdf")
def get_research_pdf(task_id: str) -> Response:
    """Return a generated PDF report for a completed research job.

    Reuses ``pdf_export.generate_pdf`` so the frontend can offer a fit-for-
    stakeholders one-click report without duplicating the layout logic.
    """
    result: AsyncResult = AsyncResult(task_id, app=celery_app)
    if result.status != "SUCCESS" or not isinstance(result.result, dict):
        return Response(
            content="Report not ready yet. Wait until research completes.",
            status_code=409,
            media_type="text/plain",
        )

    payload: dict[str, Any] = result.result
    financials_raw = payload.get("financials") or {}
    confidence_raw = payload.get("confidence") or {}

    # When the Financial Margin output couldn't be parsed into the schema
    # upstream, flow.py stores {"raw": "<model text>"}. Try to recover the
    # numbers from that text so the PDF still gets a financial table.
    if isinstance(financials_raw, dict) and set(financials_raw) == {"raw"}:
        recovered = _extract_financials_from_text(
            str(financials_raw["raw"]),
            payload.get("product_idea", "Product"),
        )
        if recovered:
            financials_raw = recovered

    financials = None
    confidence = None
    try:
        if financials_raw:
            financials = FinancialAnalysis(**financials_raw)
    except Exception:
        financials = None
    try:
        from schemas import ConfidenceScore

        if confidence_raw:
            confidence = ConfidenceScore(**confidence_raw)
    except Exception:
        confidence = None

    brief = payload.get("launch_brief", "") or ""
    competitor_report = payload.get("competitor_report", "") or ""
    product = financials.product_name if financials else payload.get("product_idea", "Product")

    summary = _build_executive_summary(payload, confidence, brief, financials, competitor_report)

    pdf_bytes = generate_pdf(product, summary, financials, confidence, brief)
    filename = f"{product.replace(' ', '_')}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _extract_financials_from_text(text: str, product_name: str) -> dict[str, Any] | None:
    """Best-effort recovery of COGS / retail / margin from unstructured text.

    Looks for the first two dollar amounts (COGS, retail) and a percentage
    (margin). Returns schema-shaped dict or ``None`` when nothing is found.
    """
    import re

    if not text:
        return None
    dollars = [float(m.replace(",", "")) for m in re.findall(r"\$\s?([\d,]+(?:\.\d{1,2})?)", text)]
    margins = [
        float(m)
        for m in re.findall(r"(\d{1,3}(?:\.\d+)?)\s?%", text)
        if 0 < float(m) <= 100
    ]
    if not dollars:
        return None
    cogs = dollars[0]
    retail = dollars[1] if len(dollars) > 1 else cogs * 2.5  # typical keystone markup
    margin = margins[0] if margins else round((retail - cogs) / retail * 100, 1)

    # Pull "Competitor N:" style lines for the price table when present.
    competitors = re.findall(r"(Competitor\s*\d+.*|[-•]\s*[A-Z][^:\n]{2,40}:\s*\$[\d.,]+.*)", text)
    return {
        "product_name": product_name,
        "estimated_cogs": cogs,
        "suggested_retail_price": retail,
        "projected_margin_percentage": margin,
        "key_competitor_prices": [c.strip() for c in competitors[:5]] or [],
    }


def _build_executive_summary(
    payload: dict[str, Any],
    confidence: Any,
    brief: str,
    financials: FinancialAnalysis | None,
    competitor_report: str = "",
) -> str:
    """Assemble an always-useful executive summary for the PDF report.

    Falls back through: LLM confidence summary → launch-brief prose →
    competitor research excerpt → synthesized line from the financials, so the
    Executive Summary section never renders as empty.
    """
    # 1) The confidence scorer usually writes the best one-liner.
    if confidence and getattr(confidence, "summary", "").strip():
        return confidence.summary.strip()

    # 2) Strip markdown headings/bullets from the launch brief into prose.
    if brief.strip():
        import re

        heading_re = re.compile(
            r"^(executive summary|target audience|competitive positioning|"
            r"pricing strategy.*|launch plan.*|risks & mitigations.*)$",
            re.IGNORECASE,
        )
        lines = []
        for ln in brief.splitlines():
            ln = ln.strip().lstrip("#").lstrip("-•* ").strip()
            if ln and not heading_re.match(ln):
                lines.append(ln)
        prose = " ".join(lines).strip()
        if prose:
            return prose[:600]

    # 3) Fall back to the raw competitor research excerpt.
    if competitor_report.strip():
        return competitor_report.strip()[:400]

    # 4) Last resort: synthesize a line from the structured financials.
    if financials:
        return (
            f"{financials.product_name}: estimated COGS of "
            f"${financials.estimated_cogs:,.2f} per unit against a suggested "
            f"retail of ${financials.suggested_retail_price:,.2f}, implying a "
            f"gross margin of {financials.projected_margin_percentage:.1f}% "
            f"across {len(financials.key_competitor_prices)} tracked competitors."
        )
    return ""