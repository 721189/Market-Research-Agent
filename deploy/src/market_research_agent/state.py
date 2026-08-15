"""Typed application state for the market research flow.

Replaces the loose state dict with a validated Pydantic model so every
field is typed and defaults are safe (no shared mutable defaults).
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class AppState(BaseModel):
    """Serializable state carried across the market research pipeline.

    Attributes:
        product_idea: The user's product idea text.
        mode: Analysis depth — ``"quick"`` (8B) or ``"deep"`` (70B).
        stage: Lifecycle stage — ``idle`` / ``running`` / ``awaiting_review`` /
            ``complete``.
        financials: Structured financial output (``FinancialAnalysis`` dict).
        launch_brief: The final Markdown go-to-market brief.
        confidence: Structured ``ConfidenceScore`` dict.
        competitor_report: Raw competitor research text.
    """

    product_idea: str = ""
    mode: str = "deep"
    stage: str = "idle"
    financials: Dict[str, Any] = Field(default_factory=dict)
    launch_brief: str = ""
    confidence: Dict[str, Any] = Field(default_factory=dict)
    competitor_report: str = ""