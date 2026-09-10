from typing import List, Dict, Any, Tuple

class ResearchValidator:
    @staticmethod
    def validate_sources(sources: List[str]) -> List[str]:
        """Deduplicates and cleans URLs"""
        seen = set()
        cleaned = []
        for s in sources:
            s_clean = s.strip().rstrip("/")
            if s_clean and s_clean not in seen:
                seen.add(s_clean)
                cleaned.append(s_clean)
        return cleaned

    @staticmethod
    def validate_competitor_data(competitors: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        issues = []
        if not competitors:
            issues.append("No competitors identified")
            return False, issues

        for c in competitors:
            if not c.get("name") or c.get("name") == "Unknown":
                issues.append("Competitor missing valid name")
            if not c.get("features"):
                issues.append(f"Competitor {c.get('name')} missing feature details")
        
        return len(issues) == 0, issues

    @staticmethod
    def validate_financial_consistency(cogs: float, price: float, margin: float) -> bool:
        if price <= 0 or cogs < 0:
            return False
        expected_margin = round(((price - cogs) / price) * 100.0, 1)
        return abs(expected_margin - margin) <= 0.5

research_validator = ResearchValidator()
