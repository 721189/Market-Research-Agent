import os
import time
import secrets
import contextvars
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator, Tuple
import logging

from backend.app.telemetry.logging import log_trace_id, log_span_id

logger = logging.getLogger("marketai.telemetry.tracing")

_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_trace_id", default=None)
_current_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_span_id", default=None)

class Span:
    def __init__(self, name: str, trace_id: str, span_id: str, parent_span_id: Optional[str] = None):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.status = "OK"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self, status: str = "OK") -> None:
        self.end_time = time.time()
        self.status = status
        duration_ms = (self.end_time - self.start_time) * 1000.0
        logger.debug(
            f"Span '{self.name}' completed in {duration_ms:.2f}ms "
            f"[trace={self.trace_id}, span={self.span_id}]",
            extra={"extra_fields": {"durationMs": duration_ms, "spanStatus": self.status, **self.attributes}}
        )

class DistributedTracer:
    """
    Standard W3C Distributed Tracer compatible with OpenTelemetry / Cloud Trace.
    Format: 00-{32-char hex trace_id}-{16-char hex span_id}-{2-char flags}
    """
    @staticmethod
    def generate_trace_id() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def generate_span_id() -> str:
        return secrets.token_hex(8)

    @classmethod
    def extract_w3c_traceparent(cls, traceparent: Optional[str]) -> Tuple[str, Optional[str]]:
        """Parses W3C traceparent header: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"""
        if not traceparent or not isinstance(traceparent, str):
            return cls.generate_trace_id(), None

        parts = traceparent.strip().split("-")
        if len(parts) == 4 and parts[0] == "00" and len(parts[1]) == 32 and len(parts[2]) == 16:
            return parts[1], parts[2]

        return cls.generate_trace_id(), None

    @classmethod
    def create_traceparent(cls, trace_id: str, span_id: str) -> str:
        return f"00-{trace_id}-{span_id}-01"

    @classmethod
    def get_current_trace_id(cls) -> str:
        tid = _current_trace_id.get()
        if not tid:
            tid = cls.generate_trace_id()
            _current_trace_id.set(tid)
            log_trace_id.set(tid)
        return tid

    @classmethod
    @contextmanager
    def start_span(
        cls,
        name: str,
        parent_traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Generator[Span, None, None]:
        """
        Creates a managed trace span with automatic context propagation and logging synchronization.
        """
        parent_span_id = None
        if parent_traceparent:
            trace_id, parent_span_id = cls.extract_w3c_traceparent(parent_traceparent)
        else:
            trace_id = _current_trace_id.get() or cls.generate_trace_id()
            parent_span_id = _current_span_id.get()

        span_id = cls.generate_span_id()
        span = Span(name, trace_id, span_id, parent_span_id)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)

        # Update context
        t_token = _current_trace_id.set(trace_id)
        s_token = _current_span_id.set(span_id)
        lt_token = log_trace_id.set(trace_id)
        ls_token = log_span_id.set(span_id)

        try:
            yield span
            span.finish("OK")
        except Exception as ex:
            span.set_attribute("error.message", str(ex))
            span.finish("ERROR")
            raise
        finally:
            _current_trace_id.reset(t_token)
            _current_span_id.reset(s_token)
            log_trace_id.reset(lt_token)
            log_span_id.reset(ls_token)

tracer = DistributedTracer()
