import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db
from backend.app.services.rate_limiter import rate_limiter
from backend.app.services.storage import storage_service
import logging

logger = logging.getLogger("marketai.health")
router = APIRouter(tags=["Health"])

@router.get("/health/live")
def health_live():
    """Liveness probe: verifies process is responding."""
    return {"status": "ok", "timestamp": time.time()}

@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """
    Readiness probe:
    Verifies connectivity, health, and latency for:
    - PostgreSQL connection pool
    - Redis (rate limiter & Celery broker)
    - S3 / Object storage
    """
    checks = {}
    is_ready = True

    # 1. PostgreSQL check & latency
    t0 = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000.0, 2)
        checks["postgres"] = {
            "status": "ok",
            "latency_ms": db_latency_ms
        }
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        checks["postgres"] = {
            "status": "error",
            "error": str(e)
        }
        is_ready = False

    # 2. Redis check
    redis_probe = rate_limiter.probe_health()
    checks["redis"] = redis_probe
    if redis_probe["status"] == "error":
        # Note: rate limiter has local in-memory failover, but report degraded
        is_ready = False

    # 3. Storage check
    storage_probe = storage_service.check_health()
    checks["storage"] = storage_probe
    if storage_probe["status"] == "error":
        is_ready = False

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "checks": checks}
        )

    return {
        "status": "ready",
        "timestamp": time.time(),
        "checks": checks
    }
