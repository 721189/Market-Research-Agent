import json
import logging
import sys
import time
import datetime
import traceback
from typing import Optional, Dict, Any
import contextvars

# Context variables for request tracing in logs
log_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_request_id", default=None)
log_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_trace_id", default=None)
log_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_span_id", default=None)
log_org_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_org_id", default=None)
log_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_job_id", default=None)
log_run_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_run_id", default=None)
log_worker_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("log_worker_id", default=None)

class StructuredJsonFormatter(logging.Formatter):
    """
    Formats standard Python log records into structured JSON for centralized
    production ingestion (Datadog, Google Cloud Logging, AWS CloudWatch, ELK).
    """
    def format(self, record: logging.LogRecord) -> str:
        timestamp_iso = datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        
        # Standard GCP/Cloud logging severity mapping
        severity_map = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL"
        }
        severity = severity_map.get(record.levelname, "DEFAULT")

        log_payload: Dict[str, Any] = {
            "timestamp": timestamp_iso,
            "severity": severity,
            "logger": record.name,
            "message": record.getMessage(),
            "component": "marketai-backend",
            "sourceLocation": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName
            }
        }

        # Correlation and distributed tracing IDs
        req_id = log_request_id.get() or getattr(record, "request_id", None)
        if req_id:
            log_payload["requestId"] = req_id

        trace_id = log_trace_id.get() or getattr(record, "trace_id", None)
        if trace_id:
            log_payload["logging.googleapis.com/trace"] = f"projects/marketai/traces/{trace_id}"
            log_payload["traceId"] = trace_id

        span_id = log_span_id.get() or getattr(record, "span_id", None)
        if span_id:
            log_payload["logging.googleapis.com/spanId"] = span_id
            log_payload["spanId"] = span_id

        org_id = log_org_id.get() or getattr(record, "org_id", None)
        if org_id:
            log_payload["tenantId"] = org_id

        job_id = log_job_id.get() or getattr(record, "job_id", None)
        if job_id:
            log_payload["jobId"] = job_id

        run_id = log_run_id.get() or getattr(record, "run_id", None)
        if run_id:
            log_payload["runId"] = run_id

        worker = log_worker_id.get() or getattr(record, "worker", None)
        if worker:
            log_payload["worker"] = worker

        # Exception details
        if record.exc_info:
            log_payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]),
                "stacktrace": traceback.format_exception(*record.exc_info)
            }

        # Extra structured attributes passed via extra={}
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_payload.update(record.extra_fields)

        return json.dumps(log_payload)

def configure_centralized_logging(log_level: str = "INFO") -> None:
    """Configures root logger with structured JSON output."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(stream_handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
