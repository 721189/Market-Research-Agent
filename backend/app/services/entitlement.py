from typing import Dict, Any, Optional, Tuple
import datetime
import logging

try:
    from sqlalchemy.orm import Session
    from backend.app.models.organization import Organization
    from backend.app.models.billing import UsageEvent, Subscription, ResearchUsage
except ImportError:
    Session = Any # type: ignore
    Organization = Any # type: ignore
    UsageEvent = Any # type: ignore
    Subscription = Any # type: ignore
    ResearchUsage = Any # type: ignore

logger = logging.getLogger("marketai.entitlement")

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
    def can_create_research(cls, org: Organization, mode: str, db: Session) -> Tuple[bool, Optional[str]]:
        """Validates tenant status, subscription active state, mode entitlement, and available monthly quota."""
        if org.status != "active":
            return False, f"Organization is currently {org.status}. Please contact support."

        if org.plan != "free":
            sub = db.query(Subscription).filter(Subscription.org_id == org.id).first()
            if sub and sub.status in ("past_due", "unpaid", "canceled"):
                return False, f"Subscription is {sub.status}. Please update payment method."

        plan_conf = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["free"])
        
        if mode not in plan_conf["allowed_modes"]:
            return False, f"Research mode '{mode}' is not available on the {org.plan.capitalize()} plan."

        now = datetime.datetime.utcnow()
        first_day_of_month = datetime.datetime(now.year, now.month, 1)
        
        # Count committed usages plus currently active reservations
        committed_count = db.query(UsageEvent).filter(
            UsageEvent.org_id == org.id,
            UsageEvent.created_at >= first_day_of_month
        ).count()

        active_reservations = db.query(ResearchUsage).filter(
            ResearchUsage.org_id == org.id,
            ResearchUsage.status == "RESERVED",
            ResearchUsage.reserved_at >= first_day_of_month
        ).count()

        total_consumed_and_pending = committed_count + active_reservations
        max_allowed = plan_conf["monthly_researches"]

        if total_consumed_and_pending >= max_allowed:
            return False, f"Monthly research quota exceeded ({total_consumed_and_pending}/{max_allowed}). Please upgrade your plan."

        return True, None

    @classmethod
    def reserve_quota(cls, db: Session, org_id: str, job_id: str, units: int = 1) -> Optional[ResearchUsage]:
        """
        Atomically creates a quota reservation for an in-flight research job.
        Uses transactional locking when available.
        """
        try:
            # Transactional row lock on organization if database supports with_for_update
            try:
                org = db.query(Organization).filter(Organization.id == org_id).with_for_update().first()
            except Exception:
                org = db.query(Organization).filter(Organization.id == org_id).first()

            if not org:
                logger.error(f"Cannot reserve quota: organization {org_id} not found")
                return None

            reservation = ResearchUsage(
                org_id=org_id,
                job_id=job_id,
                status="RESERVED",
                units_reserved=units,
                units_consumed=0,
                billing_rule="standard",
                reserved_at=datetime.datetime.utcnow()
            )
            db.add(reservation)
            db.commit()
            db.refresh(reservation)
            return reservation
        except Exception as e:
            logger.error(f"Failed to reserve research quota for job {job_id}: {e}")
            db.rollback()
            return None

    @classmethod
    def commit_quota(cls, db: Session, job_id: str, units: int = 1, billing_rule: str = "standard") -> None:
        """Finalizes a quota reservation to COMMITTED status upon successful research completion."""
        try:
            usage = db.query(ResearchUsage).filter(ResearchUsage.job_id == job_id).first()
            if usage:
                usage.status = "COMMITTED"
                usage.units_consumed = units
                usage.billing_rule = billing_rule
                usage.finalized_at = datetime.datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Failed to commit quota for job {job_id}: {e}")
            db.rollback()

    @classmethod
    def release_quota(cls, db: Session, job_id: str, reason: str = "waived_on_provider_error") -> None:
        """Releases a quota reservation if job fails or is cancelled before meaningful execution."""
        try:
            usage = db.query(ResearchUsage).filter(ResearchUsage.job_id == job_id).first()
            if usage and usage.status == "RESERVED":
                usage.status = "RELEASED"
                usage.units_consumed = 0
                usage.billing_rule = reason
                usage.finalized_at = datetime.datetime.utcnow()
                db.commit()
                logger.info(f"Released reserved quota for job {job_id} (Reason: {reason})")
        except Exception as e:
            logger.error(f"Failed to release quota for job {job_id}: {e}")
            db.rollback()

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
