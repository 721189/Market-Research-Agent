from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime

from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.auth.rbac import PERM_BILLING_VIEW
from backend.app.models.billing import UsageEvent
from backend.app.services.entitlement import PLAN_LIMITS

router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])

@router.get("/summary")
def get_usage_summary(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_BILLING_VIEW)

    now = datetime.datetime.utcnow()
    month_start = datetime.datetime(now.year, now.month, 1)

    usage_agg = db.query(
        func.count(UsageEvent.id).label("total_jobs"),
        func.sum(UsageEvent.input_tokens).label("total_input_tokens"),
        func.sum(UsageEvent.output_tokens).label("total_output_tokens"),
        func.sum(UsageEvent.search_calls).label("total_search_calls"),
        func.sum(UsageEvent.estimated_cost_usd).label("total_cost_usd")
    ).filter(
        UsageEvent.org_id == auth.organization.id,
        UsageEvent.created_at >= month_start
    ).first()

    plan_conf = PLAN_LIMITS.get(auth.organization.plan, PLAN_LIMITS["free"])

    return {
        "organization_id": auth.organization.id,
        "plan": auth.organization.plan,
        "month": now.strftime("%Y-%m"),
        "total_jobs_run": usage_agg.total_jobs or 0,
        "job_limit": plan_conf["monthly_researches"],
        "total_input_tokens": int(usage_agg.total_input_tokens or 0),
        "total_output_tokens": int(usage_agg.total_output_tokens or 0),
        "total_search_calls": int(usage_agg.total_search_calls or 0),
        "total_estimated_cost_usd": round(float(usage_agg.total_cost_usd or 0.0), 4)
    }
