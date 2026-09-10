// Shared result types matching the FastAPI backend responses.

export interface FinancialAnalysis {
  product_name: string;
  estimated_cogs: number;
  suggested_retail_price: number;
  projected_margin_percentage: number;
  key_competitor_prices: string[];
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
  stage: string;
  financials: FinancialAnalysis | Partial<FinancialAnalysis> | null;
  launch_brief: string;
  confidence: ConfidenceScore | Partial<ConfidenceScore> | null;
  competitor_report: string;
}

export interface PollResponse {
  status: string;
  task_id: string;
  result?: ResearchResult | null;
  error?: string | null;
}

export const TASK_STEPS = [
  "Competitor Scrape",
  "Financial Margin",
  "Review Gate",
  "Launch Brief",
  "Confidence Scoring",
] as const;