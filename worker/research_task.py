"""Celery task that runs the full market research pipeline headlessly.

The flow's HITL gate is driven programmatically: ``kickoff_async()`` pauses
with a ``HumanFeedbackPending`` exception, then ``resume_async("approved")``
lets the pipeline finish phase two without needing a live Streamlit session.
"""

import asyncio

from .celery_app import celery_app
from flow import auto_research_async
from logging_config import log_llm_call
from routing import get_llm_config
from tasks import validate_input


@celery_app.task(name="research.run", bind=True, max_retries=2, default_retry_delay=5)
def run_research_task(self, product_idea: str, mode: str = "deep"):
    """Research one product idea and return a JSON-serializable result dict.

    Args:
        product_idea: The product idea to research.
        mode: Analysis depth, ``"quick"`` or ``"deep"``.

    Returns:
        A dict with ``financials``, ``launch_brief``, ``confidence`` and
        ``competitor_report`` so the JSON task serializer can persist it.

    Raises:
        ValueError: If the product idea fails input validation.
    """
    validate_input(product_idea)

    try:
        payload, flow = asyncio.run(auto_research_async(product_idea, mode=mode))
    except Exception as exc:
        # Let Celery retry on transient upstream failures.
        raise self.retry(exc=exc)

    # Structured LLM call logging (guardrail observability).
    try:
        usage = getattr(flow, "usage_metrics", None)
        tokens = int(getattr(usage, "total_tokens", 0) or 0)
        cfg = get_llm_config(mode)
        if "deepinfra" in cfg["base_url"]:
            provider_label = "deepinfra"
        elif "openrouter" in cfg["base_url"]:
            provider_label = "openrouter"
        else:
            provider_label = "groq"
        log_llm_call(provider=provider_label, model=cfg["model"], tokens=tokens)
    except Exception:
        # Logging must never sink a completed job.
        pass

    return payload