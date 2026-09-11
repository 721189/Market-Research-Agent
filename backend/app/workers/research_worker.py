import asyncio
import datetime
import random
from celery.utils.log import get_task_logger
from celery.exceptions import MaxRetriesExceededError
from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.research import ResearchJob, ResearchRun, ResearchEvent
from backend.app.models.billing import UsageEvent
from backend.app.research.engine import research_engine, JobCancelledException
from backend.app.services.cost import cost_service
from backend.app.services.entitlement import entitlement_service

logger = get_task_logger(__name__)

# Non-retryable permanent failure types
FATAL_EXCEPTIONS = (
    JobCancelledException,
    ValueError,
    KeyError,
    PermissionError,
)

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_research_job(self, job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return

        # Check if cancelled before execution begins
        if job.status == "CANCELLED":
            logger.info(f"Job {job_id} already marked CANCELLED. Skipping execution.")
            return

        run_record = ResearchRun(
            job_id=job_id,
            stage="research",
            status="RUNNING",
            worker_id=str(self.request.id)
        )
        db.add(run_record)

        # State transition
        job.status = "RESEARCHING"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        # Start accurate LLM & search metering with research policy controls
        from backend.app.research.policy import get_research_policy
        policy = get_research_policy(job.mode or "quick")
        cost_service.start_job_metering(
            job.id,
            max_llm_calls=policy.max_llm_calls,
            max_context_tokens=policy.max_context_tokens
        )

        # Run real research engine async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                research_engine.run(
                    product_idea=job.product_idea,
                    mode=job.mode,
                    research_id=job.id,
                    db=db
                )
            )
        finally:
            loop.close()

        job.result = result
        run_record.status = "COMPLETED"
        run_record.completed_at = datetime.datetime.utcnow()
        db.commit()

        # Finalize and persist actual metered usage and exact USD cost
        cost_service.finalize_and_persist(
            db=db,
            org_id=job.org_id,
            job_id=job.id,
            user_id=job.creator_id,
            default_model="gemini-1.5-flash"
        )

        # Chain to Analysis Worker
        from backend.app.workers.analysis_worker import analyze_evidence_task
        analyze_evidence_task.apply_async(args=[job_id], queue="analysis")

    except JobCancelledException as e:
        logger.info(f"Research job {job_id} successfully terminated upon cancellation request: {e}")
        try:
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if job:
                job.status = "CANCELLED"
                job.cancelled_at = datetime.datetime.utcnow()
            run = db.query(ResearchRun).filter(ResearchRun.job_id == job_id, ResearchRun.status == "RUNNING").first()
            if run:
                run.status = "CANCELLED"
                run.completed_at = datetime.datetime.utcnow()
            db.commit()
            entitlement_service.release_quota(db, job_id, reason="job_cancelled")
        except Exception as db_err:
            logger.warning(f"Error persisting cancellation state for {job_id}: {db_err}")
        return

    except Exception as e:
        logger.exception(f"Error executing research job {job_id}: {e}")
        current_attempt = self.request.retries + 1
        max_attempts = self.max_retries

        # Check if error is non-retryable
        is_fatal = isinstance(e, FATAL_EXCEPTIONS)
        can_retry = not is_fatal and current_attempt <= max_attempts

        try:
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            run = db.query(ResearchRun).filter(ResearchRun.job_id == job_id, ResearchRun.status == "RUNNING").first()

            if can_retry:
                if job:
                    job.status = "RETRYING"
                    job.error_code = "TRANSIENT_EXECUTION_ERROR"
                    job.error_message = f"Attempt {current_attempt}/{max_attempts} failed: {str(e)}"
                if run:
                    run.status = "RETRYING"
                    run.error_message = str(e)
                db.commit()

                # Exponential backoff with full jitter
                base_delay = 2 ** self.request.retries * 4
                jitter = random.uniform(1.0, 4.0)
                countdown = int(min(300, base_delay + jitter))
                logger.info(f"Scheduling retry {current_attempt} for job {job_id} in {countdown}s")
                raise self.retry(exc=e, countdown=countdown)
            else:
                # Terminal failure
                if job:
                    job.status = "FAILED"
                    job.error_code = "MAX_RETRIES_EXCEEDED" if current_attempt > max_attempts else "FATAL_EXECUTION_ERROR"
                    job.error_message = f"Failed permanently: {str(e)}"
                if run:
                    run.status = "FAILED"
                    run.error_message = str(e)
                    run.completed_at = datetime.datetime.utcnow()
                db.commit()
                entitlement_service.release_quota(db, job_id, reason="terminal_execution_failure")
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for research job {job_id}")
            raise
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_quick_research_job(self, job_id: str):
    return execute_research_job(job_id)
