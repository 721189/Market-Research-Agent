"""CrewAI Flow orchestration with HITL review gate."""

from __future__ import annotations

from typing import Any, Callable

from crewai import Crew, Process
from crewai.flow import Flow, listen, start

from agents import build_agents, build_llm
from hitl import StreamlitFeedbackProvider
from schemas import ConfidenceScore
from tasks import FinancialAnalysis, create_tasks


async def run_crew_tasks(
    product_idea: str,
    mode: str,
    task_names: list[str],
    task_callback: Callable | None = None,
):
    llm = build_llm(mode)
    trend, financial, director = build_agents(llm)
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

    def __init__(self, session_state=None, task_callback=None, **kwargs):
        super().__init__(**kwargs)
        self._ss = session_state
        self._task_callback = task_callback
        self._provider = StreamlitFeedbackProvider(session_state) if session_state else None
        
        # Initialize state as a dictionary
        self.state["product_idea"] = ""
        self.state["mode"] = "deep"
        self.state["stage"] = "idle"
        self.state["financials"] = {}
        self.state["launch_brief"] = ""
        self.state["confidence"] = {}
        self.state["competitor_report"] = ""

    @start()
    async def phase_one(self):
        self.state["stage"] = "running"
        result = await run_crew_tasks(
            self.state["product_idea"],
            self.state["mode"],
            ["Competitor Scrape", "Financial Margin"],
            self._task_callback,
        )
        parsed = _parse_outputs(result)
        self.state["competitor_report"] = str(parsed.get("Competitor Scrape", ""))
        raw_fin = parsed.get("Financial Margin", {})
        if isinstance(raw_fin, FinancialAnalysis):
            self.state["financials"] = raw_fin.model_dump()
        elif isinstance(raw_fin, dict):
            self.state["financials"] = raw_fin
        else:
            self.state["financials"] = {"raw": str(raw_fin)}
        return self.state["financials"]

    @listen(phase_one)
    def review_gate(self, financials):
        """Pause for human review via Streamlit provider."""
        if self._provider:
            from crewai.flow.async_feedback.types import PendingFeedbackContext
            ctx = PendingFeedbackContext(
                flow_id=str(self.state.get("id", "flow")),
                flow_class=self.__class__.__name__,
                method_name="review_gate",
                method_output=financials,
                message="Review financial analysis before launch brief.",
                emit=["approved", "rejected"],
            )
            self._provider.request_feedback(ctx, self)
        if self._ss is not None:
            self._ss["stage"] = "awaiting_review"
        self.state["stage"] = "awaiting_review"
        return financials

    @listen("approved")
    async def phase_two(self, _financials):
        self.state["stage"] = "running"
        result = await run_crew_tasks(
            self.state["product_idea"],
            self.state["mode"],
            ["Product Launch Brief", "Confidence Scoring"],
            self._task_callback,
        )
        parsed = _parse_outputs(result)
        self.state["launch_brief"] = str(parsed.get("Product Launch Brief", ""))
        raw_conf = parsed.get("Confidence Scoring", {})
        if isinstance(raw_conf, ConfidenceScore):
            self.state["confidence"] = raw_conf.model_dump()
        elif isinstance(raw_conf, dict):
            self.state["confidence"] = raw_conf
        self.state["stage"] = "complete"
        if self._ss is not None:
            self._ss["stage"] = "complete"
        return self.state


async def kickoff_research(product_idea, mode, session_state, task_callback=None):
    flow = MarketResearchFlow(session_state=session_state, task_callback=task_callback)
    flow.state["product_idea"] = product_idea
    flow.state["mode"] = mode
    result = await flow.kickoff_async()
    return result, flow


async def resume_research(flow: MarketResearchFlow, feedback: str = "approved"):
    return await flow.resume_async(feedback=feedback)