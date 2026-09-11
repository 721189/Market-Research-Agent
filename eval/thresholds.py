import sys
import logging
from typing import Dict, Any, Tuple
from eval.evaluator import EvalMetrics

logger = logging.getLogger("marketai.eval.thresholds")

# Production Release Gates
RELEASE_THRESHOLDS = {
    "unsupported_claim_rate_max": 2.0,       # unsupported factual claims < 2%
    "citation_accuracy_min": 95.0,           # citation correctness > 95%
    "financial_arithmetic_accuracy_min": 100.0, # financial arithmetic = 100%
    "hallucination_rate_max": 1.0,           # hallucination rate < 1%
    "competitor_recall_min": 70.0,           # competitor recall >= 70%
    "competitor_precision_min": 85.0         # competitor precision >= 85%
}

class ReleaseGateValidator:
    @staticmethod
    def validate_metrics(metrics: EvalMetrics) -> Tuple[bool, list[str]]:
        """Validates AI benchmark metrics against strict production release thresholds."""
        failures = []

        if metrics.unsupported_claim_rate > RELEASE_THRESHOLDS["unsupported_claim_rate_max"]:
            failures.append(
                f"UNSUPPORTED_CLAIMS: {metrics.unsupported_claim_rate}% exceeds limit of {RELEASE_THRESHOLDS['unsupported_claim_rate_max']}%"
            )

        if metrics.citation_accuracy < RELEASE_THRESHOLDS["citation_accuracy_min"]:
            failures.append(
                f"CITATION_ACCURACY: {metrics.citation_accuracy}% below minimum {RELEASE_THRESHOLDS['citation_accuracy_min']}%"
            )

        if metrics.financial_arithmetic_accuracy < RELEASE_THRESHOLDS["financial_arithmetic_accuracy_min"]:
            failures.append(
                f"FINANCIAL_ARITHMETIC: {metrics.financial_arithmetic_accuracy}% below required {RELEASE_THRESHOLDS['financial_arithmetic_accuracy_min']}%"
            )

        if metrics.hallucination_rate > RELEASE_THRESHOLDS["hallucination_rate_max"]:
            failures.append(
                f"HALLUCINATION_RATE: {metrics.hallucination_rate}% exceeds max {RELEASE_THRESHOLDS['hallucination_rate_max']}%"
            )

        passed = len(failures) == 0
        return passed, failures

    @classmethod
    def enforce_or_fail(cls, metrics: EvalMetrics) -> None:
        passed, failures = cls.validate_metrics(metrics)
        if not passed:
            logger.error("AI Evaluation Release Gate FAILED:")
            for f in failures:
                logger.error(f"  - {f}")
            raise RuntimeError(f"Release gate check failed: {'; '.join(failures)}")
        logger.info("AI Evaluation Release Gate PASSED all threshold criteria.")

release_validator = ReleaseGateValidator()
