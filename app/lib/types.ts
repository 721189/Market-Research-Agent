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
  product_name?: string;
  entry_tier_usd?: number;
  mid_tier_usd?: number;
  enterprise_tier_usd?: number;
  estimated_cogs?: number;
  suggested_retail_price?: number;
  gross_margin_pct?: number;
  breakeven_units_monthly?: number;
  sensitivity_scenarios?: Record<string, unknown>;
  key_competitor_prices?: string[];
}

export interface ConfidenceScore {
  overall_score: number;
  source_reliability: number;
  evidence_coverage: number;
  consistency: number;
  high_confidence_insights: string[];
  low_confidence_insights: string[];
  summary: string;
}

export interface ResearchResult {
  product_idea: string;
  mode: string;
  stage?: string;
  evidence_sources?: EvidenceRecord[];
  structured_claims?: StructuredClaim[];
  competitors?: Record<string, unknown>[];
  market_dynamics?: Record<string, unknown>;
  pricing_landscape?: Record<string, unknown>;
  customer_profile?: Record<string, unknown>;
  financials: FinancialAnalysis | null;
  confidence: ConfidenceScore | null;
  launch_brief?: string;
  report?: Record<string, unknown>;
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