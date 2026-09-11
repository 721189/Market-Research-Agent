from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class SLODefinition:
    name: str
    target_percentage: float
    description: str
    measurement_window: str
    error_budget_percentage: float

PRODUCTION_SLOS: Dict[str, SLODefinition] = {
    "api_availability": SLODefinition(
        name="API Availability",
        target_percentage=99.9,
        description="Percentage of successful (non-5xx) responses across all REST endpoints",
        measurement_window="30d rolling",
        error_budget_percentage=0.1
    ),
    "api_p95_latency": SLODefinition(
        name="API p95 Latency",
        target_percentage=95.0, # 95% of requests completed under 500ms
        description="API request duration < 500ms for synchronous endpoints",
        measurement_window="30d rolling",
        error_budget_percentage=5.0
    ),
    "job_enqueue_reliability": SLODefinition(
        name="Job Enqueue Success",
        target_percentage=99.9,
        description="Percentage of research job submissions reliably acknowledged into broker",
        measurement_window="30d rolling",
        error_budget_percentage=0.1
    ),
    "research_completion_rate": SLODefinition(
        name="Research Completion Success",
        target_percentage=98.0,
        description="Percentage of research runs reaching COMPLETED status without unhandled errors",
        measurement_window="30d rolling",
        error_budget_percentage=2.0
    ),
    "sse_reconnect_recovery": SLODefinition(
        name="SSE Reconnect Recovery",
        target_percentage=99.0,
        description="Percentage of SSE clients replaying events within 5 seconds of disconnect",
        measurement_window="30d rolling",
        error_budget_percentage=1.0
    ),
    "report_generation_rate": SLODefinition(
        name="PDF Report Generation Success",
        target_percentage=99.0,
        description="Percentage of report generation jobs successfully rendered and signed",
        measurement_window="30d rolling",
        error_budget_percentage=1.0
    ),
    "billing_webhook_success": SLODefinition(
        name="Billing Webhook Reliability",
        target_percentage=99.99,
        description="Percentage of Stripe invoice & subscription webhooks processed idempotently",
        measurement_window="30d rolling",
        error_budget_percentage=0.01
    )
}

class SLOCalculator:
    @staticmethod
    def evaluate_slo_compliance(
        total_requests: int,
        failed_requests: int,
        slo_key: str
    ) -> Dict[str, Any]:
        slo = PRODUCTION_SLOS.get(slo_key)
        if not slo or total_requests == 0:
            return {"status": "UNKNOWN", "compliance_rate": 100.0}

        success_requests = max(0, total_requests - failed_requests)
        compliance_rate = round((success_requests / total_requests) * 100.0, 3)
        meets_slo = compliance_rate >= slo.target_percentage

        return {
            "slo_name": slo.name,
            "target": f"{slo.target_percentage}%",
            "current_compliance": f"{compliance_rate}%",
            "meets_slo": meets_slo,
            "status": "HEALTHY" if meets_slo else "BUDGET_EXHAUSTED"
        }

slo_calculator = SLOCalculator()
