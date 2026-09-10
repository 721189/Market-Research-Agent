from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.auth.rbac import PERM_RESEARCH_CREATE, PERM_RESEARCH_VIEW, PERM_RESEARCH_CANCEL
from backend.app.models.research import ResearchJob, ResearchEvent
from backend.app.schemas.research import (
    ResearchCreateRequest,
    ResearchResponse,
    ResearchDetailResponse,
    ResearchEventResponse
)
from backend.app.services.entitlement import entitlement_service
from backend.app.services.rate_limiter import rate_limiter
from backend.app.services.storage import storage_service
from backend.app.workers.tasks import execute_research_job, execute_quick_research_job, celery_app

router = APIRouter(prefix="/api/v1/research", tags=["Research"])

@router.post("", response_model=ResearchResponse, status_code=status.HTTP_202_ACCEPTED)
def create_research_job(
    payload: ResearchCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    # 1. RBAC check (Phase 11)
    auth.require_permission(PERM_RESEARCH_CREATE)

    # 2. Rate limiting check (Phase 14): 10 jobs/minute per organization
    if not rate_limiter.check_rate_limit(f"org:{auth.organization.id}:jobs", limit=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before scheduling more research jobs."
        )

    # 3. Entitlement check (Phase 17)
    if not entitlement_service.can_create_research(auth.organization, payload.mode, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plan limits reached or mode not permitted on your subscription tier."
        )

    # 4. Idempotency handling (Phase 13 & 20)
    if payload.idempotency_key:
        existing = db.query(ResearchJob).filter(
            ResearchJob.org_id == auth.organization.id,
            ResearchJob.idempotency_key == payload.idempotency_key
        ).first()
        if existing:
            return ResearchResponse(
                task_id=existing.id,
                status=existing.status,
                mode=existing.mode,
                created_at=existing.created_at
            )

    # 5. Insert new ResearchJob
    job = ResearchJob(
        org_id=auth.organization.id,
        creator_id=auth.user.id,
        status="QUEUED",
        mode=payload.mode,
        product_idea=payload.product_idea,
        idempotency_key=payload.idempotency_key,
        priority=5,
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 6. Dispatch to Celery Queue (Phase 3 & 12)
    queue_name = "research.quick" if payload.mode == "quick" else "research.deep"
    if payload.mode == "quick":
        execute_quick_research_job.apply_async(args=[job.id], queue=queue_name)
    else:
        execute_research_job.apply_async(args=[job.id], queue=queue_name)

    return ResearchResponse(
        task_id=job.id,
        status=job.status,
        mode=job.mode,
        created_at=job.created_at
    )

@router.get("/{task_id}", response_model=ResearchDetailResponse)
def get_research_job(
    task_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_RESEARCH_VIEW)

    job = db.query(ResearchJob).filter(ResearchJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found")

    # Strict Tenant Isolation (Phase 10)
    if job.org_id != auth.organization.id and not auth.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to job in other tenant denied")

    pdf_download_url = None
    if job.pdf_object_key:
        try:
            pdf_download_url = storage_service.generate_signed_url(job.pdf_object_key, expires_in=3600)
        except Exception:
            pdf_download_url = None

    return ResearchDetailResponse(
        task_id=job.id,
        status=job.status,
        progress=job.progress,
        mode=job.mode,
        product_idea=job.product_idea,
        result=job.result,
        pdf_ready=bool(job.pdf_object_key),
        pdf_download_url=pdf_download_url,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )

@router.post("/{task_id}/cancel")
def cancel_research_job(
    task_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_RESEARCH_CANCEL)

    job = db.query(ResearchJob).filter(ResearchJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found")

    if job.org_id != auth.organization.id and not auth.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
        return {"message": f"Job already in terminal state: {job.status}"}

    job.status = "CANCELLED"
    job.cancelled_at = datetime.datetime.utcnow()
    db.commit()

    return {"message": "Job cancellation initiated successfully", "status": "CANCELLED"}

@router.get("/{task_id}/events", response_model=List[ResearchEventResponse])
def get_research_events(
    task_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_RESEARCH_VIEW)

    job = db.query(ResearchJob).filter(ResearchJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.org_id != auth.organization.id and not auth.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    events = db.query(ResearchEvent).filter(
        ResearchEvent.job_id == task_id
    ).order_by(ResearchEvent.created_at.asc()).all()

    return [
        ResearchEventResponse(
            stage=e.stage,
            progress=e.progress,
            message=e.message,
            level=e.level,
            created_at=e.created_at
        )
        for e in events
    ]
