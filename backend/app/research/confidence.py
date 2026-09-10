from typing import List, Dict, Any
from urllib.parse import urlparse
import math

class ConfidenceEngine:
    @staticmethod
    def calculate_confidence(
        sources: List[Dict[str, Any]],
        claims_count: int,
        cross_source_agreements: int,
        calculation_valid: bool
    ) -> Dict[str, Any]:
        """
        Observable evidence-based confidence scoring engine:
        - 25% source reliability (mean authority score modulated by domain diversification)
        - 20% freshness (mean freshness score)
        - 25% evidence coverage (sufficient claims & sources)
        - 20% cross-source agreement
        - 10% calculation consistency
        """
        risk_factors: List[str] = []
        strengths: List[str] = []

        if not sources:
            return {
                "overall_score": 35,
                "tier": "INSUFFICIENT",
                "risk_factors": ["No external verifiable evidence sources were retrieved."],
                "strengths": [],
                "breakdown": {
                    "source_reliability": 30.0,
                    "freshness": 40.0,
                    "evidence_coverage": 20.0,
                    "cross_source_agreement": 30.0,
                    "calculation_consistency": 50.0,
                    "domain_diversity": 0.0
                }
            }

        # 1. Source Reliability & Domain Diversification
        valid_authorities = []
        domains = []
        for s in sources:
            auth = s.get("authority_score")
            if isinstance(auth, (int, float)) and 0 <= auth <= 100:
                valid_authorities.append(float(auth))
            else:
                valid_authorities.append(50.0)

            url = s.get("url", "")
            domain = s.get("domain") or (urlparse(url).netloc.lower() if url else "unknown")
            domains.append(domain)

        raw_mean_authority = sum(valid_authorities) / max(1, len(valid_authorities))

        # Domain concentration check
        unique_domains = len(set(d for d in domains if d and d != "unknown"))
        total_valid_domains = max(1, len(domains))
        domain_diversity_ratio = unique_domains / total_valid_domains

        diversity_penalty = 1.0
        if total_valid_domains >= 3:
            if domain_diversity_ratio < 0.4:
                diversity_penalty = 0.75
                risk_factors.append(f"High domain concentration: only {unique_domains} distinct domains across {total_valid_domains} sources.")
            elif domain_diversity_ratio < 0.6:
                diversity_penalty = 0.90
                risk_factors.append("Moderate domain concentration in cited evidence.")
            else:
                strengths.append(f"High domain diversity across {unique_domains} independent sources.")

        source_reliability = raw_mean_authority * diversity_penalty

        # 2. Freshness (20%)
        valid_freshness = []
        for s in sources:
            fresh = s.get("freshness_score")
            if isinstance(fresh, (int, float)) and 0 <= fresh <= 100:
                valid_freshness.append(float(fresh))
            else:
                valid_freshness.append(50.0)

        mean_freshness = sum(valid_freshness) / max(1, len(valid_freshness))
        if mean_freshness < 60:
            risk_factors.append("Average evidence age exceeds 180 days.")
        else:
            strengths.append("Evidence base contains fresh and timely market observations.")

        # 3. Evidence Coverage (25%)
        # Benchmarked: at least 5 verified sources and 6 claims gives full 100%
        safe_claims = max(0, claims_count)
        source_coverage_factor = min(1.0, len(sources) / 5.0) * 50.0
        claims_coverage_factor = min(1.0, safe_claims / 6.0) * 50.0
        coverage_score = min(100.0, source_coverage_factor + claims_coverage_factor)

        if len(sources) < 3:
            risk_factors.append("Limited source volume (fewer than 3 primary sources).")
        if safe_claims < 3:
            risk_factors.append("Sparse quantitative claim coverage extracted from market documents.")

        # 4. Cross-source Agreement (20%)
        agreement_ratio = cross_source_agreements / max(1, len(sources))
        agreement_score = min(100.0, max(40.0, agreement_ratio * 100.0))
        if agreement_score >= 80:
            strengths.append("High multi-source concordance on pricing and competitor positioning.")

        # 5. Calculation Consistency (10%)
        if calculation_valid:
            calc_score = 100.0
            strengths.append("Unit economics and financial formulas passed deterministic verification.")
        else:
            calc_score = 0.0
            risk_factors.append("Arithmetic divergence detected in financial projections.")

        overall = (
            0.25 * source_reliability
            + 0.20 * mean_freshness
            + 0.25 * coverage_score
            + 0.20 * agreement_score
            + 0.10 * calc_score
        )

        overall = int(round(min(100.0, max(0.0, overall))))

        # Determine Tier
        if overall >= 80:
            tier = "HIGH"
        elif overall >= 65:
            tier = "MODERATE"
        elif overall >= 50:
            tier = "LOW"
        else:
            tier = "INSUFFICIENT"

        return {
            "overall_score": overall,
            "tier": tier,
            "risk_factors": risk_factors,
            "strengths": strengths,
            "breakdown": {
                "source_reliability": round(source_reliability, 1),
                "freshness": round(mean_freshness, 1),
                "evidence_coverage": round(coverage_score, 1),
                "cross_source_agreement": round(agreement_score, 1),
                "calculation_consistency": round(calc_score, 1),
                "domain_diversity": round(domain_diversity_ratio * 100.0, 1)
            }
        }

confidence_engine = ConfidenceEngine()
