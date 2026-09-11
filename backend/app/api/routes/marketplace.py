import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.models.marketplace import ResearchTemplate, ScheduledResearch, MarketAlert
from backend.app.services.marketplace import marketplace_service

router = APIRouter(prefix="/api/v1/marketplace", tags=["Marketplace & Intelligence"])

@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    """Lists available public market research templates."""
    db_templates = db.query(ResearchTemplate).filter(ResearchTemplate.is_public == True).all()
    if db_templates:
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "mode": t.mode,
                "prompt_template": t.prompt_template,
                "default_parameters": t.default_parameters,
            }
            for t in db_templates
        ]
    return marketplace_service.list_templates()

@router.get("/templates/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    """Retrieves a specific market research template."""
    tmpl = db.query(ResearchTemplate).filter(ResearchTemplate.id == template_id).first()
    if tmpl:
        return {
            "id": tmpl.id,
            "title": tmpl.title,
            "description": tmpl.description,
            "category": tmpl.category,
            "mode": tmpl.mode,
            "prompt_template": tmpl.prompt_template,
            "default_parameters": tmpl.default_parameters,
        }
    fallback = marketplace_service.get_template(template_id)
    if not fallback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return fallback

@router.get("/schedules")
def list_schedules(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Lists scheduled recurring research tasks for the tenant organization."""
    schedules = db.query(ScheduledResearch).filter(
        ScheduledResearch.org_id == auth.organization.id,
        ScheduledResearch.is_active == True
    ).order_by(ScheduledResearch.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "product_idea": s.product_idea,
            "mode": s.mode,
            "cron_schedule": s.cron_schedule,
            "is_active": s.is_active,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "created_at": s.created_at.isoformat()
        }
        for s in schedules
    ]

@router.post("/schedules", status_code=status.HTTP_201_CREATED)
def create_schedule(
    product_idea: str,
    cron_schedule: str = "0 9 * * 1",
    mode: str = "quick",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Schedules a recurring market research run."""
    schedule_id = f"sched_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.utcnow()
    next_run = now + datetime.timedelta(days=7) # Default weekly run

    schedule = ScheduledResearch(
        id=schedule_id,
        org_id=auth.organization.id,
        creator_id=auth.user.id,
        product_idea=product_idea,
        mode=mode,
        cron_schedule=cron_schedule,
        is_active=True,
        next_run_at=next_run,
        created_at=now
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return {
        "id": schedule.id,
        "product_idea": schedule.product_idea,
        "cron_schedule": schedule.cron_schedule,
        "mode": schedule.mode,
        "next_run_at": schedule.next_run_at.isoformat(),
        "status": "SCHEDULED"
    }

@router.delete("/schedules/{schedule_id}")
def cancel_schedule(
    schedule_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Deactivates a scheduled research task."""
    schedule = db.query(ScheduledResearch).filter(
        ScheduledResearch.id == schedule_id,
        ScheduledResearch.org_id == auth.organization.id
    ).first()

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    schedule.is_active = False
    db.commit()
    return {"message": "Scheduled research task deactivated successfully", "id": schedule_id}

@router.get("/alerts")
def list_alerts(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Retrieves market intelligence alerts for the tenant organization."""
    alerts = db.query(MarketAlert).filter(
        MarketAlert.org_id == auth.organization.id
    ).order_by(MarketAlert.created_at.desc()).limit(50).all()

    return [
        {
            "id": a.id,
            "product_idea": a.product_idea,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "headline": a.headline,
            "details": a.details,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

@router.post("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """Marks a market intelligence alert as read."""
    alert = db.query(MarketAlert).filter(
        MarketAlert.id == alert_id,
        MarketAlert.org_id == auth.organization.id
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read", "id": alert_id}
