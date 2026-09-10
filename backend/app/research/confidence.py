from typing import List, Dict, Any

class ConfidenceEngine:
    @staticmethod
    def calculate_confidence(
        sources: List[Dict[str, Any]],
        claims_count: int,
        cross_source_agreements: int,
        calculation_valid: bool
    ) -> Dict[str, Any]:
        """
        Observable evidence-based confidence scoring:
        - 25% source reliability (mean authority score)
        - 20% freshness (mean freshness score)
        - 25% evidence coverage (sufficient claims & sources)
        - 20% cross-source agreement
        - 10% calculation consistency
        """
        if not sources:
            return {
                "overall_score": 40,
                "breakdown": {
                    "source_reliability": 40,
                    "freshness": 50,
                    "evidence_coverage": 30,
                    "cross_source_agreement": 30,
                    "calculation_consistency": 50
                }
            }

        # 1. Source Reliability (25%)
        mean_authority = sum(s.get("authority_score", 50) for s in sources) / len(sources)
        
        # 2. Freshness (20%)
        mean_freshness = sum(s.get("freshness_score", 50) for s in sources) / len(sources)
        
        # 3. Evidence Coverage (25%)
        # Benchmarked: at least 5 sources and 5 claims gives 100%
        coverage_score = min(100.0, (len(sources) / 5.0 * 50.0) + (claims_count / 5.0 * 50.0))
        
        # 4. Cross-source Agreement (20%)
        # Benchmarked on validated concordances
        agreement_score = min(100.0, (cross_source_agreements / max(1, len(sources))) * 100.0)
        agreement_score = max(50.0, agreement_score)
        
        # 5. Calculation Consistency (10%)
        calc_score = 100.0 if calculation_valid else 0.0

        overall = (
            0.25 * mean_authority
            + 0.20 * mean_freshness
            + 0.25 * coverage_score
            + 0.20 * agreement_score
            + 0.10 * calc_score
        )

        overall = int(round(min(100.0, max(0.0, overall))))

        return {
            "overall_score": overall,
            "breakdown": {
                "source_reliability": round(mean_authority, 1),
                "freshness": round(mean_freshness, 1),
                "evidence_coverage": round(coverage_score, 1),
                "cross_source_agreement": round(agreement_score, 1),
                "calculation_consistency": round(calc_score, 1)
            }
        }

confidence_engine = ConfidenceEngine()
