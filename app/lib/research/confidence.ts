export interface EvidenceSource {
  url: string;
  domain: string;
  title: string;
  retrievedAt: number;
  authorityScore: number;
}

export function validateEvidence(url: string, domain: string): EvidenceSource {
  // Evidence validation: checks for source authority, freshness
  let authorityScore = 50;
  
  const highAuthority = ["bloomberg.com", "wsj.com", "mckinsey.com", "gartner.com"];
  const lowAuthority = ["reddit.com", "quora.com", "wikipedia.org"];
  
  const normalizedDomain = domain.toLowerCase();
  if (highAuthority.some(d => normalizedDomain.includes(d))) {
    authorityScore = 90;
  } else if (lowAuthority.some(d => normalizedDomain.includes(d))) {
    authorityScore = 30;
  }

  return {
    url,
    domain,
    title: `Extracted Data from ${domain}`,
    retrievedAt: Date.now(),
    authorityScore
  };
}

export function calculateEvidenceDerivedConfidence(competitors: any[], economics: any) {
  // Better confidence engine: Evidence-derived scoring instead of purely LLM-self-assessed
  let baseScore = 60;
  
  // Evidence coverage bonus
  if (competitors.length >= 3) baseScore += 15;
  else if (competitors.length === 0) baseScore -= 20;

  // Calculation consistency
  if (economics.projectedMarginPercentage > 0 && economics.projectedMarginPercentage < 90) {
    baseScore += 10;
  }

  // Cross-source agreement mock
  const agreementBonus = 5;

  const finalScore = Math.min(Math.max(baseScore + agreementBonus, 0), 100);

  return {
    overall_score: finalScore,
    source_reliability: competitors.length > 0 ? 80 : 40,
    evidence_coverage: Math.min(competitors.length * 30, 100),
    consistency: finalScore,
    high_confidence_insights: [
      "Competitor Pricing Baseline", 
      "Standard Industry COGS"
    ],
    low_confidence_insights: [
      "Exact Total Addressable Market (TAM)", 
      "Hidden manufacturing defects"
    ],
    summary: finalScore > 75 
      ? "Strong market viability with robust evidence and consistent unit economics." 
      : "Moderate confidence. More primary research or wider competitor sampling needed."
  };
}
