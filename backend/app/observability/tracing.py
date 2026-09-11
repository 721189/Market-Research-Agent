import logging
from typing import Optional, Any
from contextlib import contextmanager

logger = logging.getLogger("marketai.tracing")

class TracingManager:
    """OpenTelemetry & Distributed Tracing Wrapper."""

    def __init__(self):
        self.tracer = None
        self._init_opentelemetry()

    def _init_opentelemetry(self):
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            
            provider = TracerProvider()
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer("marketai.telemetry")
        except ImportError:
            self.tracer = None

    @contextmanager
    def span(self, name: str, attributes: Optional[dict] = None):
        """Creates an OpenTelemetry span context."""
        if self.tracer:
            with self.tracer.start_as_current_span(name) as sp:
                if attributes:
                    for k, v in attributes.items():
                        sp.set_attribute(k, str(v))
                yield sp
        else:
            # Fallback no-op
            yield None

tracing = TracingManager()
