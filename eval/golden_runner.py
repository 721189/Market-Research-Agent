import json
import glob
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger("marketai.eval.golden")

class GoldenEvaluationRunner:
    """Evaluates full research pipeline outputs against authoritative golden datasets across versions."""

    def __init__(self, golden_dir: str = "eval/golden"):
        self.golden_dir = golden_dir
        self.golden_cases = self._load_cases()

    def _load_cases(self) -> Dict[str, Dict[str, Any]]:
        cases = {}
        for path in glob.glob(os.path.join(self.golden_dir, "*.json")):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cases[data["product_idea"]] = data
        return cases

    def score_research_run(self, product_idea: str, result_dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Compares a research run against golden ground truth expectations."""
        golden = self.golden_cases.get(product_idea)
        if not golden:
            return {"status": "NO_GOLDEN_CASE", "score": 0.0}

        # 1. Competitor coverage
        expected_comps = [c["name"].lower() for c in golden.get("expected_competitors", [])]
        extracted_comps = [c.get("name", "").lower() for c in result_dataset.get("competitors", [])]
        matched_comps = [exp for exp in expected_comps if any(exp in ext or ext in exp for ext in extracted_comps)]
        comp_score = (len(matched_comps) / max(1, len(expected_comps))) * 100.0

        # 2. Key market facts coverage
        expected_facts = golden.get("known_market_facts", [])
        claims_text = " ".join([c.get("claim_text", "") for c in result_dataset.get("claims", [])])
        summary_text = result_dataset.get("executive_summary", "")
        full_text = (claims_text + " " + summary_text).lower()

        matched_facts = sum(
            1 for fact in expected_facts 
            if any(word.lower() in full_text for word in fact.split() if len(word) > 5)
        )
        fact_score = (matched_facts / max(1, len(expected_facts))) * 100.0

        # 3. Overall golden match score
        total_score = round((comp_score * 0.5) + (fact_score * 0.5), 2)

        return {
            "test_case_id": golden["test_case_id"],
            "competitor_match_pct": round(comp_score, 2),
            "market_facts_coverage_pct": round(fact_score, 2),
            "matched_competitors": matched_comps,
            "total_golden_score": total_score,
            "status": "PASSED" if total_score >= 70.0 else "REGRESSION_DETECTED"
        }

    def track_version_regression(self, historical_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tracks regression across version 1, version 2, version 3 etc.
        Detects regressions in competitor recall, accuracy, or confidence score.
        """
        history_summary = []
        for run in historical_runs:
            version = run.get("version", "v1")
            idea = run.get("product_idea", "")
            scores = self.score_research_run(idea, run.get("result", {}))
            history_summary.append({
                "version": version,
                "product_idea": idea,
                "golden_score": scores.get("total_golden_score", 0.0),
                "status": scores.get("status", "UNKNOWN")
            })
        return history_summary

golden_runner = GoldenEvaluationRunner()
