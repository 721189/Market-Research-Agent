"""CrewAI Flow orchestration with HITL review gate."""

from __future__ import annotations

from typing import Any, Callable

from crewai import Crew, Process
from crewai.flow import Flow, listen, start

from agents import build_agents
from hitl import StreamlitFeedbackProvider
from schemas import ConfidenceScore
from state import AppState
from tasks import FinancialAnalysis, create_tasks, summarize_context, validate_input


async def run_crew_tasks(
    product_idea: str,
    mode: str,
    task_names: list[str],
    task_callback: Callable | None = None,
):
    trend, financial, director = build_agents(complexity=mode)
    comp, fin, launch, conf = create_tasks(product_idea, trend, financial, director)
    task_map = {
        "Competitor Scrape": comp,
        "Financial Margin": fin,
        "Product Launch Brief": launch,
        "Confidence Scoring": conf,
    }
    tasks = [task_map[n] for n in task_names]
    agents = list({t.agent for t in tasks})
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        task_callback=task_callback,
    )
    return await crew.kickoff_async(inputs={})


def _parse_outputs(result) -> dict[str, Any]:
    outputs = getattr(result, "tasks_output", []) or []
    out: dict[str, Any] = {}
    for o in outputs:
        name = getattr(o, "name", None) or getattr(getattr(o, "task", None), "name", "")
        raw = getattr(o, "raw", o)
        out[name] = raw
    return out


class MarketResearchFlow(Flow):
    """Research pipeline: scrape → HITL review → launch + confidence."""

    def __init__(self, session_state=None, task_callback=None, initial_state=None, **kwargs):
        super().__init__(**kwargs)
        self._ss = session_state
        self._task_callback = task_callback
        self._provider = StreamlitFeedbackProvider(session_state) if session_state else None

        # Typed, validated state. ``state`` is a read-only property inherited
        # from the CrewAI Flow base, so we seed the underlying ``_state`` with
        # an AppState (or the supplied ``initial_state``).
        self._state = initial_state if initial_state is not None else AppState()

    @start()
    async def phase_one(self):
        self.state.stage = "running"
        result = await run_crew_tasks(
            self.state.product_idea,
            self.state.mode,
            ["Competitor Scrape", "Financial Margin"],
            self._task_callback,
        )
        parsed = _parse_outputs(result)
        self.state.competitor_report = summarize_context(str(parsed.get("Competitor Scrape", "")))
        raw_fin = parsed.get("Financial Margin", {})
        if isinstance(raw_fin, FinancialAnalysis):
            self.state.financials = raw_fin.model_dump()
        elif isinstance(raw_fin, dict):
            self.state.financials = raw_fin
        else:
            self.state.financials = {"raw": str(raw_fin)}
        return self.state.financials

    @listen(phase_one)
    def review_gate(self, financials):
        """Pause for human review via Streamlit provider."""
        if self._provider:
            from crewai.flow.async_feedback.types import PendingFeedbackContext
            ctx = PendingFeedbackContext(
                flow_id=str(getattr(self.state, "id", None) or self.flow_id or "flow"),
                flow_class=self.__class__.__name__,
                method_name="review_gate",
                method_output=financials,
                message="Review financial analysis before launch brief.",
                emit=["approved", "rejected"],
            )
            self._provider.request_feedback(ctx, self)
        if self._ss is not None:
            self._ss["stage"] = "awaiting_review"
        self.state.stage = "awaiting_review"
        return financials

    @listen("approved")
    async def phase_two(self, _financials):
        self.state.stage = "running"
        result = await run_crew_tasks(
            self.state.product_idea,
            self.state.mode,
            ["Product Launch Brief", "Confidence Scoring"],
            self._task_callback,
        )
        parsed = _parse_outputs(result)
        self.state.launch_brief = str(parsed.get("Product Launch Brief", ""))
        raw_conf = parsed.get("Confidence Scoring", {})
        if isinstance(raw_conf, ConfidenceScore):
            self.state.confidence = raw_conf.model_dump()
        elif isinstance(raw_conf, dict):
            self.state.confidence = raw_conf
        self.state.stage = "complete"
        if self._ss is not None:
            self._ss["stage"] = "complete"
        return self.state


async def kickoff_research(product_idea, mode, session_state, task_callback=None):
    validate_input(product_idea)
    flow = MarketResearchFlow(
        session_state=session_state,
        task_callback=task_callback,
        initial_state=AppState(product_idea=product_idea, mode=mode),
    )
    result = await flow.kickoff_async()
    return result, flow


async def auto_research_async(product_idea: str, mode: str = "deep"):
    """Headless full-pipeline run used by the Celery worker.

    Kicks off the flow and, at the HITL gate, auto-approves so phase two
    (launch brief + confidence) completes without a live session.

    Returns:
        A ``(payload: dict, flow)`` tuple where ``payload`` is the
        JSON-serializable result dict.
    """
    validate_input(product_idea)
    from crewai.flow.async_feedback.types import HumanFeedbackPending

    flow = MarketResearchFlow(
        session_state={},  # minimal dict enables the HITL provider pause
        initial_state=AppState(product_idea=product_idea, mode=mode),
    )
    try:
        await flow.kickoff_async()
    except HumanFeedbackPending:
        await flow.resume_async("approved")

    payload = {
        "product_idea": flow.state.product_idea,
        "mode": flow.state.mode,
        "stage": flow.state.stage,
        "financials": flow.state.financials,
        "launch_brief": flow.state.launch_brief,
        "confidence": flow.state.confidence,
        "competitor_report": flow.state.competitor_report,
    }
    return payload, flow


async def resume_research(flow: MarketResearchFlow, feedback: str = "approved"):
    return await flow.resume_async(feedback=feedback)