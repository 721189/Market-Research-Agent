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
    def reserve_quota_and_create_job_transactional(
        cls,
        db: Session,
        org: Organization,
        creator_id: str,
        mode: str,
        product_idea: str,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Optional[Any], Optional[str]]:
        """
        Truly transactional quota reservation and job creation:
        1. Lock organization row with with_for_update()
        2. Recalculate month-to-date committed usage + active reservations
        3. Validate against plan limit
        4. Create ResearchJob and ResearchUsage reservation in same transaction
        5. Commit atomically
        """
        try:
            # 1. Lock organization row
            try:
                locked_org = db.query(Organization).filter(Organization.id == org.id).with_for_update().first()
            except Exception:
                locked_org = db.query(Organization).filter(Organization.id == org.id).first()

            if not locked_org or locked_org.status != "active":
                return None, f"Organization is currently {locked_org.status if locked_org else 'not found'}."

            plan_conf = PLAN_LIMITS.get(locked_org.plan, PLAN_LIMITS["free"])
            if mode not in plan_conf["allowed_modes"]:
                return None, f"Research mode '{mode}' is not permitted on the {locked_org.plan.capitalize()} plan."

            # 2. Recalculate current month's usage
            now = datetime.datetime.utcnow()
            first_day_of_month = datetime.datetime(now.year, now.month, 1)

            committed_count = db.query(UsageEvent).filter(
                UsageEvent.org_id == locked_org.id,
                UsageEvent.created_at >= first_day_of_month
            ).count()

            active_reservations = db.query(ResearchUsage).filter(
                ResearchUsage.org_id == locked_org.id,
                ResearchUsage.status == "RESERVED",
                ResearchUsage.reserved_at >= first_day_of_month
            ).count()

            total_consumed_and_pending = committed_count + active_reservations
            max_allowed = plan_conf["monthly_researches"]

            if total_consumed_and_pending >= max_allowed:
                return None, f"Monthly research quota exceeded ({total_consumed_and_pending}/{max_allowed})."

            # 3. Create job and reservation in same atomic block
            from backend.app.models.research import ResearchJob
            job = ResearchJob(
                org_id=locked_org.id,
                creator_id=creator_id,
                status="QUEUED",
                mode=mode,
                product_idea=product_idea,
                idempotency_key=idempotency_key,
                priority=5,
                progress=0
            )
            db.add(job)
            db.flush() # Populate job.id before reservation FK

            reservation = ResearchUsage(
                org_id=locked_org.id,
                job_id=job.id,
                status="RESERVED",
                units_reserved=1,
                units_consumed=0,
                billing_rule="standard",
                reserved_at=now
            )
            db.add(reservation)

            # 4. Atomic Commit
            db.commit()
            db.refresh(job)
            return job, None
        except Exception as e:
            db.rollback()
            logger.error(f"Transactional quota reservation failed for org {org.id}: {e}")
            return None, str(e)

    @classmethod
    def reserve_quota(cls, db: Session, org_id: str, job_id: str, mode: str = "quick", units: int = 1) -> Optional[ResearchUsage]:
        """
        Atomically checks limits and creates a quota reservation for an in-flight research job.
        Strict transactional sequence: Lock -> recalculate -> reserve.
        """
        try:
            # 1. Transactional row lock on organization
            try:
                org = db.query(Organization).filter(Organization.id == org_id).with_for_update().first()
            except Exception:
                org = db.query(Organization).filter(Organization.id == org_id).first()

            if not org:
                logger.error(f"Cannot reserve quota: organization {org_id} not found")
                return None

            if org.status != "active":
                logger.warning(f"Organization {org_id} is inactive ({org.status})")
                return None

            plan_conf = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["free"])
            if mode not in plan_conf.get("allowed_modes", ["quick"]):
                logger.warning(f"Mode '{mode}' not permitted for plan '{org.plan}'")
                return None

            # 2. Recalculate usage under lock
            now = datetime.datetime.utcnow()
            first_day_of_month = datetime.datetime(now.year, now.month, 1)

            committed_count = db.query(UsageEvent).filter(
                UsageEvent.org_id == org_id,
                UsageEvent.created_at >= first_day_of_month
            ).count()

            active_reservations = db.query(ResearchUsage).filter(
                ResearchUsage.org_id == org_id,
                ResearchUsage.status == "RESERVED",
                ResearchUsage.reserved_at >= first_day_of_month
            ).count()

            total_consumed = committed_count + active_reservations
            max_allowed = plan_conf.get("monthly_researches", 10)

            # 3. Check quota limit
            if total_consumed >= max_allowed:
                logger.warning(f"Quota limit reached for org {org_id}: {total_consumed}/{max_allowed}")
                return None

            # 4. Create reservation object (part of active transaction)
            reservation = ResearchUsage(
                org_id=org_id,
                job_id=job_id,
                status="RESERVED",
                units_reserved=units,
                units_consumed=0,
                billing_rule="standard",
                reserved_at=now
            )
            db.add(reservation)
            return reservation
        except Exception as e:
            logger.error(f"Failed to reserve research quota for job {job_id}: {e}")
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
