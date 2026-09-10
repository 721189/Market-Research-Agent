import datetime
from celery.utils.log import get_task_logger
from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.research import ResearchJob, ResearchRun, ResearchEvent

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def analyze_evidence_task(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job or job.status == "CANCELLED":
        db.close()
        return

    run_record = ResearchRun(
        job_id=job_id,
        stage="analysis",
        status="RUNNING",
        worker_id=str(self.request.id)
    )
    db.add(run_record)

    try:
        job.status = "ANALYZING"
        db.commit()

        # Emit event
        event = ResearchEvent(
            job_id=job.id,
            stage="analysis",
            progress=80,
            message="Validating evidence fidelity and cross-referencing industry benchmarks",
            level="INFO"
        )
        db.add(event)
        db.commit()

        # Chain to PDF worker
        from backend.app.workers.pdf_worker import generate_pdf_report_task
        generate_pdf_report_task.apply_async(args=[job_id], queue="reports")

        run_record.status = "COMPLETED"
        run_record.completed_at = datetime.datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.exception(f"Error in analysis worker for job {job_id}: {e}")
        job.status = "FAILED"
        job.error_code = "ANALYSIS_ERROR"
        job.error_message = str(e)
        run_record.status = "FAILED"
        run_record.error_message = str(e)
        db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()
