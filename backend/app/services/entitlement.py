from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.organization import Organization
from backend.app.models.billing import UsageEvent, Subscription
import datetime

PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "monthly_researches": 10,
        "allowed_modes": ["quick"],
        "can_export_pdf": True,
        "can_use_api": False,
        "max_team_members": 2,
    },
    "starter": {
        "monthly_researches": 50,
        "allowed_modes": ["quick", "deep"],
        "can_export_pdf": True,
        "can_use_api": True,
        "max_team_members": 5,
    },
    "pro": {
        "monthly_researches": 250,
        "allowed_modes": ["quick", "deep", "batch"],
        "can_export_pdf": True,
        "can_use_api": True,
        "max_team_members": 15,
    },
    "enterprise": {
        "monthly_researches": 10000,
        "allowed_modes": ["quick", "deep", "batch"],
        "can_export_pdf": True,
        "can_use_api": True,
        "max_team_members": 999,
    },
}

class EntitlementService:
    @classmethod
    def can_create_research(cls, org: Organization, mode: str, db: Session) -> bool:
        # Check tenant organization lifecycle status
        if org.status != "active":
            return False

        # Check subscription status for paid tiers
        if org.plan != "free":
            sub = db.query(Subscription).filter(Subscription.org_id == org.id).first()
            if sub and sub.status in ("past_due", "unpaid", "canceled"):
                return False

        plan_conf = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["free"])
        
        # Check mode entitlement
        if mode not in plan_conf["allowed_modes"]:
            return False

        # Check monthly usage quota
        now = datetime.datetime.utcnow()
        first_day_of_month = datetime.datetime(now.year, now.month, 1)
        
        job_count = db.query(UsageEvent).filter(
            UsageEvent.org_id == org.id,
            UsageEvent.created_at >= first_day_of_month
        ).count()

        return job_count < plan_conf["monthly_researches"]

    @classmethod
    def can_export_pdf(cls, org: Organization) -> bool:
        plan_conf = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["free"])
        return plan_conf.get("can_export_pdf", True)

    @classmethod
    def can_use_api(cls, org: Organization) -> bool:
        if org.status != "active":
            return False
        plan_conf = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["free"])
        return plan_conf.get("can_use_api", False)

entitlement_service = EntitlementService()
