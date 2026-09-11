// Shared TypeScript contracts strictly matching FastAPI backend schemas

export interface EvidenceRecord {
  url: string;
  domain: string;
  authority_score: number;
  freshness_score: number;
  content_hash: string;
  snippet?: string;
  title?: string;
}

export interface StructuredClaim {
  claim_text: string;
  claim_type: string;
  value?: string | null;
  unit?: string | null;
  confidence: number;
  verification_status: string;
  agreement_ratio: string;
  verbatim_quote?: string | null;
  sources: string[];
}

export interface FinancialAnalysis {
  estimated_cogs: number;
  suggested_retail_price: number;
  projected_margin_percentage: number;
  markup_percentage: number;
  break_even_units: number;
  pricing_basis: string;
  assumption_type: string;
  scenarios: Record<string, unknown>;
}

export interface ConfidenceScore {
  overall_score: number;
  dimension_scores: Record<string, number>;
  reasoning: string[];
}

export interface ResearchResult {
  product_idea: string;
  mode: string;
  pipeline_state: string;
  executive_summary: string;
  strategic_recommendations: string[];
  swot_analysis: Record<string, unknown>;
  go_to_market: Record<string, unknown>;
  market_dynamics: Record<string, unknown>;
  pricing_landscape: Record<string, unknown>;
  customer_profile: Record<string, unknown>;
  competitors: Record<string, unknown>[];
  claims: StructuredClaim[];
  cross_source_agreement: Record<string, unknown>;
  financials: FinancialAnalysis;
  confidence: ConfidenceScore;
  evidence_sources: EvidenceRecord[];
}

export interface ResearchDetailResponse {
  task_id: string;
  status: string;
  progress: number;
  mode: string;
  product_idea: string;
  result?: ResearchResult | null;
  pdf_ready: boolean;
  pdf_download_url?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface PollResponse {
  task_id: string;
  status: string;
  progress: number;
  result?: ResearchResult | null;
  error_message?: string | null;
  pdf_ready?: boolean;
  pdf_download_url?: string | null;
}

export const TASK_STEPS = [
  "Planning & Research Strategy",
  "Evidence Harvesting & Verification",
  "Structured Claim Extraction",
  "Financial Sensitivity Modeling",
  "Strategic Synthesis & Report Generation",
] as const;