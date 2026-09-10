import asyncio
import datetime
from celery.utils.log import get_task_logger
from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.research import ResearchJob, ResearchRun
from backend.app.models.billing import UsageEvent
from backend.app.research.engine import research_engine
from backend.app.services.cost import cost_service

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_research_job(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found")
        db.close()
        return

    # Check if cancelled
    if job.status == "CANCELLED":
        logger.info(f"Job {job_id} was cancelled")
        db.close()
        return

    run_record = ResearchRun(
        job_id=job_id,
        stage="research",
        status="RUNNING",
        worker_id=str(self.request.id)
    )
    db.add(run_record)

    try:
        # State transition (Phase 12)
        job.status = "RESEARCHING"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        # Run real research engine async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            research_engine.run(
                product_idea=job.product_idea,
                mode=job.mode,
                research_id=job.id,
                db=db
            )
        )
        loop.close()

        job.result = result
        run_record.status = "COMPLETED"
        run_record.completed_at = datetime.datetime.utcnow()
        db.commit()

        # Log usage & cost (Phase 15)
        cost_usd = cost_service.calculate_cost(
            model="gemini-1.5-flash",
            input_tokens=2500,
            output_tokens=1500,
            search_calls=len(result.get("evidence_sources", []))
        )
        usage = UsageEvent(
            org_id=job.org_id,
            job_id=job.id,
            user_id=job.creator_id,
            provider="google-gemini",
            model="gemini-1.5-flash",
            input_tokens=2500,
            output_tokens=1500,
            search_calls=len(result.get("evidence_sources", [])),
            estimated_cost_usd=cost_usd
        )
        db.add(usage)
        db.commit()

        # Chain to Analysis Worker
        from backend.app.workers.analysis_worker import analyze_evidence_task
        analyze_evidence_task.apply_async(args=[job_id], queue="analysis")

    except Exception as e:
        logger.exception(f"Error in research worker for job {job_id}: {e}")
        job.status = "FAILED"
        job.error_code = "RESEARCH_EXECUTION_ERROR"
        job.error_message = str(e)
        run_record.status = "FAILED"
        run_record.error_message = str(e)
        db.commit()
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def execute_quick_research_job(self, job_id: str):
    return execute_research_job(job_id)
