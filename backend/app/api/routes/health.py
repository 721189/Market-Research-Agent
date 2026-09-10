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
    return {"status": "ok"}

@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """
    Readiness probe (Phase 22):
    Verifies connectivity to:
    - PostgreSQL
    - Redis
    - S3 / Object Storage
    """
    checks = {}
    
    # 1. Postgres check
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        checks["postgres"] = f"error: {str(e)}"

    # 2. Redis check
    try:
        if rate_limiter.redis:
            rate_limiter.redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unconfigured"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = f"error: {str(e)}"

    # 3. S3 check
    try:
        storage_service.client.list_buckets()
        checks["storage"] = "ok"
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        checks["storage"] = f"error: {str(e)}"

    is_healthy = all(v == "ok" for k, v in checks.items() if k != "redis" or rate_limiter.redis is not None)
    
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "checks": checks}
        )

    return {"status": "ready", "checks": checks}
