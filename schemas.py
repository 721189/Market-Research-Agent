"""Pydantic schemas for structured crew outputs."""

from pydantic import BaseModel, Field


class ConfidenceScore(BaseModel):
    """Trust layer: 0-100 score with breakdown."""

    overall_score: int = Field(ge=0, le=100)
    source_reliability: int = Field(ge=0, le=100)
    evidence_coverage: int = Field(ge=0, le=100)
    consistency: int = Field(ge=0, le=100)
    high_confidence_insights: list[str] = Field(default_factory=list)
    low_confidence_insights: list[str] = Field(default_factory=list)
    summary: str = ""
