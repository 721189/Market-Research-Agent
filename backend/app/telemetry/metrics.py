import time
import threading
from typing import Dict, Tuple, List, Optional
import logging

logger = logging.getLogger("marketai.telemetry.metrics")

class MetricLock:
    def __init__(self):
        self._lock = threading.Lock()

class Counter:
    def __init__(self, name: str, description: str, label_names: Tuple[str, ...] = ()):
        self.name = name
        self.description = description
        self.label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels) -> None:
        if amount < 0:
            raise ValueError("Counter increments must be non-negative")
        key = tuple(str(labels.get(l, "")) for l in self.label_names)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def collect(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter"
        ]
        with self._lock:
            for key, val in sorted(self._values.items()):
                if self.label_names:
                    label_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key))
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return lines

class Gauge:
    def __init__(self, name: str, description: str, label_names: Tuple[str, ...] = ()):
        self.name = name
        self.description = description
        self.label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels) -> None:
        key = tuple(str(labels.get(l, "")) for l in self.label_names)
        with self._lock:
            self._values[key] = float(value)

    def inc(self, amount: float = 1.0, **labels) -> None:
        key = tuple(str(labels.get(l, "")) for l in self.label_names)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels) -> None:
        self.inc(-amount, **labels)

    def collect(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge"
        ]
        with self._lock:
            for key, val in sorted(self._values.items()):
                if self.label_names:
                    label_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key))
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return lines

class Histogram:
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, description: str, label_names: Tuple[str, ...] = (), buckets: Tuple[float, ...] = DEFAULT_BUCKETS):
        self.name = name
        self.description = description
        self.label_names = label_names
        self.buckets = sorted(buckets) + [float("inf")]
        self._counts: Dict[Tuple[str, ...], int] = {}
        self._sums: Dict[Tuple[str, ...], float] = {}
        self._bucket_counts: Dict[Tuple[str, ...], Dict[float, int]] = {}
        self._lock = threading.Lock()

    def observe(self, value: float, **labels) -> None:
        key = tuple(str(labels.get(l, "")) for l in self.label_names)
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            self._sums[key] = self._sums.get(key, 0.0) + value
            if key not in self._bucket_counts:
                self._bucket_counts[key] = {b: 0 for b in self.buckets}
            for b in self.buckets:
                if value <= b:
                    self._bucket_counts[key][b] += 1

    def collect(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram"
        ]
        with self._lock:
            for key in sorted(self._counts.keys()):
                base_labels = []
                if self.label_names:
                    base_labels = [f'{k}="{v}"' for k, v in zip(self.label_names, key)]

                # Buckets
                b_dict = self._bucket_counts[key]
                for b in self.buckets:
                    b_str = "+Inf" if b == float("inf") else str(b)
                    b_label = f'le="{b_str}"'
                    full_labels = ",".join(base_labels + [b_label]) if base_labels else b_label
                    lines.append(f"{self.name}_bucket{{{full_labels}}} {b_dict[b]}")

                labels_str = f"{{{','.join(base_labels)}}}" if base_labels else ""
                lines.append(f"{self.name}_count{labels_str} {self._counts[key]}")
                lines.append(f"{self.name}_sum{labels_str} {self._sums[key]}")
        return lines

# Registry of Core Metrics
http_requests_total = Counter(
    "marketai_http_requests_total",
    "Total incoming HTTP requests processed",
    ("method", "endpoint", "status")
)

http_request_duration_seconds = Histogram(
    "marketai_http_request_duration_seconds",
    "HTTP request processing latency in seconds",
    ("method", "endpoint")
)

research_jobs_total = Counter(
    "marketai_research_jobs_total",
    "Total market research executions dispatched",
    ("mode", "status")
)

research_job_duration_seconds = Histogram(
    "marketai_research_job_duration_seconds",
    "Total end-to-end execution time of research jobs in seconds",
    ("mode",),
    buckets=(5.0, 10.0, 20.0, 45.0, 90.0, 180.0, 300.0)
)

llm_tokens_total = Counter(
    "marketai_llm_tokens_total",
    "Total LLM tokens metered across models",
    ("model", "type") # type: input, output
)

llm_cost_usd_total = Counter(
    "marketai_llm_cost_usd_total",
    "Total cumulative dollar cost incurred from LLM and search calls",
    ("model",)
)

security_events_total = Counter(
    "marketai_security_events_total",
    "Total security policy enforcements triggered",
    ("event_type", "action") # event_type: ssrf_block, prompt_injection, invalid_token
)

active_workers_gauge = Gauge(
    "marketai_active_workers_gauge",
    "Current active Celery worker processes reporting heartbeat"
)

celery_queue_depth = Gauge(
    "marketai_celery_queue_depth",
    "Estimated pending jobs in Celery task queues",
    ("queue",)
)

ALL_METRICS = [
    http_requests_total,
    http_request_duration_seconds,
    research_jobs_total,
    research_job_duration_seconds,
    llm_tokens_total,
    llm_cost_usd_total,
    security_events_total,
    active_workers_gauge,
    celery_queue_depth
]

def generate_prometheus_metrics() -> str:
    """Generates standard Prometheus text exposition format response."""
    output = []
    for metric in ALL_METRICS:
        output.extend(metric.collect())
    return "\n".join(output) + "\n"
