from typing import List, Dict, Any, Tuple
from backend.app.research.evidence import evidence_collector

class ResearchValidator:
    @staticmethod
    def validate_sources(sources: List[str]) -> List[str]:
        """
        Deduplicates and canonicalizes URLs:
        - Strips marketing trackers
        - Drops malformed or private targets
        - Returns unique, standardized URLs
        """
        seen = set()
        cleaned = []
        for s in sources:
            if not isinstance(s, str):
                continue
            canonical = evidence_collector.canonicalize_url(s)
            if canonical and canonical not in seen:
                seen.add(canonical)
                cleaned.append(canonical)
        return cleaned

    @staticmethod
    def validate_competitor_data(competitors: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        issues = []
        if not competitors:
            issues.append("No competitors identified")
            return False, issues

        seen_names = set()
        for idx, c in enumerate(competitors):
            name = (c.get("name") or "").strip()
            if not name or name.lower() in ("unknown", "n/a", "none"):
                issues.append(f"Competitor at index {idx} missing valid name")
            elif name.lower() in seen_names:
                issues.append(f"Duplicate competitor identified: '{name}'")
            else:
                seen_names.add(name.lower())

            features = c.get("features")
            if not features or not isinstance(features, list) or len(features) == 0:
                issues.append(f"Competitor '{name}' missing feature details")
        
        return len(issues) == 0, issues

    @staticmethod
    def validate_financial_consistency(cogs: float, price: float, margin: float, cac: float = 0.0, contribution_margin: float = None) -> bool:
        """
        Verifies mathematical consistency across unit economics:
        1. Price must be strictly positive
        2. COGS must be non-negative
        3. Gross Margin % == ((Price - COGS) / Price) * 100 within 0.5% tolerance
        4. Contribution Margin per unit cannot exceed Gross Profit (since total variable costs >= direct COGS)
        """
        try:
            if price <= 0 or cogs < 0:
                return False
            
            # Gross profit calculation
            expected_profit = max(0.0, price - cogs)
            expected_margin = round((expected_profit / price) * 100.0, 1) if price > 0 else 0.0
            
            if abs(expected_margin - margin) > 0.5:
                return False

            if contribution_margin is not None:
                # Contribution margin (Price - Variable Costs) cannot logically exceed Gross Profit (Price - Direct COGS)
                if contribution_margin > (expected_profit + 0.1):
                    return False

            return True
        except Exception:
            return False

research_validator = ResearchValidator()
