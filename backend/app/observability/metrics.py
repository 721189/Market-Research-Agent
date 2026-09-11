import time
from typing import Dict, Any, Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    # 1. API Metrics
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests received",
        ["method", "endpoint", "status_code", "org_id"]
    )
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    HTTP_REQUEST_SIZE_BYTES = Histogram(
        "http_request_size_bytes",
        "HTTP request payload size in bytes",
        ["endpoint"],
        buckets=[100, 1000, 10000, 100000, 1000000]
    )

    # 2. Queue & Worker Metrics
    QUEUE_DEPTH = Gauge(
        "celery_queue_depth",
        "Current number of pending tasks in Celery queue",
        ["queue_name"]
    )
    QUEUE_TASK_AGE_SECONDS = Histogram(
        "celery_task_wait_seconds",
        "Time task spent waiting in queue before worker pickup",
        ["queue_name"],
        buckets=[1, 5, 15, 30, 60, 120, 300]
    )
    TASK_DURATION_SECONDS = Histogram(
        "celery_task_duration_seconds",
        "Execution duration of celery tasks",
        ["task_name", "queue_name", "status"],
        buckets=[5, 15, 30, 60, 120, 300, 600]
    )
    TASK_FAILURES_TOTAL = Counter(
        "celery_task_failures_total",
        "Total task failures",
        ["task_name", "error_code"]
    )
    WORKER_UTILIZATION_PCT = Gauge(
        "celery_worker_utilization_percent",
        "Worker active tasks vs capacity",
        ["worker_name"]
    )

    # 3. AI & LLM Gateway Metrics
    LLM_CALLS_TOTAL = Counter(
        "llm_calls_total",
        "Total discrete LLM calls",
        ["provider", "model", "status_code"]
    )
    LLM_TOKENS_TOTAL = Counter(
        "llm_tokens_total",
        "Total tokens consumed",
        ["provider", "model", "token_type"] # input or output
    )
    LLM_DURATION_SECONDS = Histogram(
        "llm_duration_seconds",
        "LLM API latency",
        ["provider", "model"],
        buckets=[0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0]
    )
    LLM_COST_USD_TOTAL = Counter(
        "llm_cost_usd_total",
        "Accumulated LLM cost in USD",
        ["org_id", "model"]
    )

    # 4. Research Quality Metrics
    RESEARCH_COMPLETION_TOTAL = Counter(
        "research_completion_total",
        "Research jobs terminal outcomes",
        ["mode", "outcome"] # completed, partial, failed, cancelled
    )
    CITATION_FAILURES_TOTAL = Counter(
        "citation_failures_total",
        "Total claims failing citation verification",
        ["reason"]
    )
    CONFIDENCE_SCORE_DISTRIBUTION = Histogram(
        "research_confidence_score",
        "Confidence score calculated for research jobs",
        ["tier"], # HIGH, MEDIUM, LOW
        buckets=[20, 40, 60, 70, 80, 90, 100]
    )

    # 5. Billing & Revenue Metrics
    ACTIVE_SUBSCRIPTIONS = Gauge(
        "billing_active_subscriptions",
        "Number of active paying subscriptions",
        ["plan"]
    )
    FAILED_PAYMENTS_TOTAL = Counter(
        "billing_failed_payments_total",
        "Total failed invoice payments",
        ["currency"]
    )
    ESTIMATED_MRR_USD = Gauge(
        "billing_estimated_mrr_usd",
        "Estimated Monthly Recurring Revenue in USD"
    )

class MetricsService:
    @staticmethod
    def record_http_request(method: str, endpoint: str, status_code: int, duration: float, org_id: str = "anon", size_bytes: int = 0):
        if PROMETHEUS_AVAILABLE:
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code), org_id=org_id).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
            if size_bytes > 0:
                HTTP_REQUEST_SIZE_BYTES.labels(endpoint=endpoint).observe(size_bytes)

    @staticmethod
    def record_llm_execution(provider: str, model: str, input_tokens: int, output_tokens: int, duration_sec: float, cost_usd: float, org_id: str, success: bool = True, status_code: int = 200):
        if PROMETHEUS_AVAILABLE:
            LLM_CALLS_TOTAL.labels(provider=provider, model=model, status_code=str(status_code)).inc()
            LLM_TOKENS_TOTAL.labels(provider=provider, model=model, token_type="input").inc(input_tokens)
            LLM_TOKENS_TOTAL.labels(provider=provider, model=model, token_type="output").inc(output_tokens)
            LLM_DURATION_SECONDS.labels(provider=provider, model=model).observe(duration_sec)
            LLM_COST_USD_TOTAL.labels(org_id=org_id, model=model).inc(cost_usd)

    @staticmethod
    def record_research_outcome(mode: str, outcome: str, confidence_score: int):
        if PROMETHEUS_AVAILABLE:
            RESEARCH_COMPLETION_TOTAL.labels(mode=mode, outcome=outcome).inc()
            tier = "HIGH" if confidence_score >= 80 else ("MEDIUM" if confidence_score >= 60 else "LOW")
            CONFIDENCE_SCORE_DISTRIBUTION.labels(tier=tier).observe(confidence_score)

metrics_service = MetricsService()
