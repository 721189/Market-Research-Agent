from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EvidenceRecordSchema(BaseModel):
    url: str
    domain: str
    authority_score: int
    freshness_score: int
    content_hash: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None

class StructuredClaimSchema(BaseModel):
    claim_text: str
    claim_type: str
    value: Optional[str] = None
    unit: Optional[str] = None
    confidence: int
    verification_status: str
    agreement_ratio: str
    sources: List[str] = Field(default_factory=list)

class FinancialAnalysisSchema(BaseModel):
    estimated_cogs: float
    suggested_retail_price: float
    projected_margin_percentage: float
    markup_percentage: float
    break_even_units: int
    pricing_basis: str
    assumption_type: str = "benchmark_assumption"
    scenarios: Dict[str, Any]

class ConfidenceScoreSchema(BaseModel):
    overall_score: int
    dimension_scores: Dict[str, int]
    reasoning: List[str]

class ResearchResult(BaseModel):
    product_idea: str
    mode: str
    pipeline_state: str
    executive_summary: str
    strategic_recommendations: List[str] = Field(default_factory=list)
    swot_analysis: Dict[str, Any] = Field(default_factory=dict)
    go_to_market: Dict[str, Any] = Field(default_factory=dict)
    market_dynamics: Dict[str, Any] = Field(default_factory=dict)
    pricing_landscape: Dict[str, Any] = Field(default_factory=dict)
    customer_profile: Dict[str, Any] = Field(default_factory=dict)
    competitors: List[Dict[str, Any]] = Field(default_factory=list)
    claims: List[StructuredClaimSchema] = Field(default_factory=list)
    cross_source_agreement: Dict[str, Any] = Field(default_factory=dict)
    financials: FinancialAnalysisSchema
    confidence: ConfidenceScoreSchema
    evidence_sources: List[EvidenceRecordSchema] = Field(default_factory=list)

class ResearchCreateRequest(BaseModel):
    product_idea: str = Field(..., min_length=3, max_length=2000, description="Product idea or concept to research")
    mode: str = Field("deep", pattern="^(quick|deep|batch)$")
    idempotency_key: Optional[str] = Field(None, max_length=255)

class ResearchResponse(BaseModel):
    task_id: str
    status: str
    mode: str
    created_at: datetime

class ResearchEventResponse(BaseModel):
    stage: str
    progress: int
    message: str
    level: str
    created_at: datetime

class ResearchDetailResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    mode: str
    product_idea: str
    result: Optional[ResearchResult] = None
    pdf_ready: bool = False
    pdf_download_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
