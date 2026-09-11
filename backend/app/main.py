import time
import uuid
import logging
from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextlib import asynccontextmanager
from backend.app.config import settings
from backend.app.db.session import engine, Base, wait_for_db
from backend.app.services.storage import storage_service
from backend.app.api.routes import health, research, reports, usage, billing, marketplace, apikeys
from backend.app.telemetry.logging import configure_centralized_logging, log_request_id, log_trace_id, log_span_id
from backend.app.telemetry.tracing import tracer
from backend.app.telemetry.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    generate_prometheus_metrics
)
from backend.app.telemetry.alerting import alert_engine

# Setup enterprise centralized structured JSON logging
configure_centralized_logging(settings.LOG_LEVEL)
logger = logging.getLogger("marketai.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Verifying database connectivity on startup...")
    db_connected = wait_for_db(max_retries=5, initial_delay=1.0)
    if db_connected:
        logger.info("Database connection established successfully. Schema managed by Alembic migrations.")
    else:
        logger.error("Database connection could not be established after maximum retries. Operating in degraded state.")

    # Storage initialization
    storage_service.resilient_init(max_retries=3)

    yield

    # Graceful shutdown sequence
    logger.info("Shutting down API server and disposing database connection pool...")
    try:
        engine.dispose()
        logger.info("Database pool disposed cleanly.")
    except Exception as e:
        logger.warning(f"Error disposing database pool: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Authoritative Enterprise Market Research Analysis Engine",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Distributed Tracing, Correlation ID, Latency & Prometheus Metrics Middleware
@app.middleware("http")
async def telemetry_and_tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    traceparent = request.headers.get("traceparent")
    trace_id, parent_span_id = tracer.extract_w3c_traceparent(traceparent)
    span_id = tracer.generate_span_id()

    # Set context vars for structured logging
    req_token = log_request_id.set(request_id)
    tr_token = log_trace_id.set(trace_id)
    sp_token = log_span_id.set(span_id)

    request.state.request_id = request_id
    request.state.trace_id = trace_id
    request.state.span_id = span_id

    endpoint = request.url.path
    start_time = time.time()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        process_time_s = time.time() - start_time
        process_time_ms = process_time_s * 1000.0

        # Prometheus metrics recording
        http_requests_total.inc(method=request.method, endpoint=endpoint, status=str(status_code))
        http_request_duration_seconds.observe(process_time_s, method=request.method, endpoint=endpoint)
        alert_engine.record_request(is_error=(status_code >= 500))

        # Outbound tracing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["traceparent"] = tracer.create_traceparent(trace_id, span_id)
        response.headers["X-Response-Time"] = f"{process_time_ms:.2f}ms"
        return response
    except Exception as exc:
        process_time_s = time.time() - start_time
        process_time_ms = process_time_s * 1000.0
        http_requests_total.inc(method=request.method, endpoint=endpoint, status="500")
        http_request_duration_seconds.observe(process_time_s, method=request.method, endpoint=endpoint)
        alert_engine.record_request(is_error=True)

        logger.exception(f"Unhandled exception on request {request_id}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred processing your request.",
                    "request_id": request_id,
                    "trace_id": trace_id
                }
            },
            headers={
                "X-Request-ID": request_id,
                "X-Trace-ID": trace_id,
                "traceparent": tracer.create_traceparent(trace_id, span_id)
            }
        )
    finally:
        log_request_id.reset(req_token)
        log_trace_id.reset(tr_token)
        log_span_id.reset(sp_token)

# Standard error response formatting (Phase 16 & 20)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "request_id": request_id,
                "trace_id": trace_id
            }
        },
        headers={"X-Request-ID": request_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "request_id": request_id,
                "trace_id": trace_id,
                "details": exc.errors()
            }
        },
        headers={"X-Request-ID": request_id}
    )

# Prometheus standard metrics exposition endpoint
@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def get_metrics():
    return PlainTextResponse(
        generate_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

# Real-time alert status endpoint
@app.get("/alerts", include_in_schema=False)
def get_alerts():
    firing = alert_engine.evaluate_all()
    return {
        "status": "FIRING" if firing else "HEALTHY",
        "active_alerts_count": len(firing),
        "alerts": firing
    }

# Register routers
app.include_router(health.router)
app.include_router(research.router)
app.include_router(reports.router)
app.include_router(usage.router)
app.include_router(billing.router)
app.include_router(marketplace.router)
app.include_router(apikeys.router)
