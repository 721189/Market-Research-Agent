import datetime
import logging
from celery.utils.log import get_task_logger
from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.auth import Organization
from backend.app.models.marketplace import ScheduledResearch
from backend.app.services.entitlement import entitlement_service
from backend.app.workers.tasks import execute_research_job, execute_quick_research_job

logger = get_task_logger(__name__)

@celery_app.task(name="scheduler.dispatch_scheduled_research")
def dispatch_scheduled_research():
    """
    Poller task that runs every minute to dispatch due scheduled research jobs.
    Uses the exact same quota engine and standard pipeline as manual jobs.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        # Find active schedules that are due
        due_schedules = db.query(ScheduledResearch).filter(
            ScheduledResearch.is_active == True,
            ScheduledResearch.next_run_at <= now
        ).all()

        for schedule in due_schedules:
            logger.info(f"Dispatching scheduled research {schedule.id} for org {schedule.org_id}")
            
            org = db.query(Organization).filter(Organization.id == schedule.org_id).first()
            if not org:
                continue

            # Use the real entitlement transactional logic
            job, err_reason = entitlement_service.reserve_quota_and_create_job_transactional(
                db=db,
                org=org,
                creator_id=schedule.creator_id,
                mode=schedule.mode,
                product_idea=schedule.product_idea,
                idempotency_key=f"sched_{schedule.id}_{now.strftime('%Y%m%d%H%M')}"
            )

            if job:
                # Dispatch to standard pipeline
                queue_name = "research.quick" if schedule.mode == "quick" else "research.deep"
                try:
                    if schedule.mode == "quick":
                        execute_quick_research_job.apply_async(args=[job.id], queue=queue_name)
                    else:
                        execute_research_job.apply_async(args=[job.id], queue=queue_name)
                    
                    # Update schedule last_run and next_run
                    schedule.last_run_at = now
                    # Basic 7 day increment for now (in a real system, parse cron_schedule)
                    schedule.next_run_at = now + datetime.timedelta(days=7)
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to dispatch schedule {schedule.id} to celery: {e}")
                    entitlement_service.release_quota(db, job.id, reason="queue_dispatch_failure")
                    job.status = "FAILED"
                    job.error_code = "DISPATCH_ERROR"
                    db.commit()
            else:
                logger.warning(f"Could not dispatch schedule {schedule.id}: {err_reason}")

    except Exception as e:
        logger.exception(f"Error in scheduler worker: {e}")
    finally:
        db.close()
