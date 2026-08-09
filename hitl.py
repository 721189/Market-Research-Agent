"""Streamlit-native HITL provider for CrewAI Flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from crewai.flow.async_feedback.types import HumanFeedbackPending, PendingFeedbackContext

if TYPE_CHECKING:
    from crewai.flow import Flow


class StreamlitFeedbackProvider:
    """Pauses flow and stores pending context in session_state."""

    def __init__(self, session_state: Any):
        self._ss = session_state

    def request_feedback(self, context: PendingFeedbackContext, flow: Flow) -> None:
        self._ss["stage"] = "awaiting_review"
        self._ss["hitl_context"] = context.to_dict()
        self._ss["pending_flow"] = flow
        raise HumanFeedbackPending(context=context)
