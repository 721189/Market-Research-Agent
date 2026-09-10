from .celery_app import celery_app
from .database import SessionLocal
from .models import ResearchJob
import time
import os
import boto3

@celery_app.task(bind=True, max_retries=3)
def execute_research_job(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        return
        
    try:
        job.status = "RESEARCHING"
        db.commit()
        
        # 16. Parallel research execution & abstraction (Mocked LLM execution time)
        time.sleep(2) 
        
        # Transition to Analysis Phase
        job.status = "ANALYZING"
        db.commit()
        
        # Delegate to dedicated analysis workers
        analyze_evidence.apply_async(args=[job_id], queue="analysis")
        
    except Exception as e:
        job.status = "FAILED"
        db.commit()
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def analyze_evidence(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    
    try:
        # 20. Deterministic financial engine runs here
        time.sleep(2)
        
        job.status = "GENERATING_REPORT"
        
        # Construct result
        job.result = {
            "product_idea": job.product_idea,
            "financials": {
                "estimated_cogs": 10.5,
                "suggested_retail_price": 29.99,
                "projected_margin_percentage": 65,
                "key_competitor_prices": ["Competitor A: $25"]
            },
            "confidence": {"overall_score": 92}
        }
        db.commit()
        
        generate_pdf_report.apply_async(args=[job_id], queue="reports")
        
    except Exception as e:
        job.status = "FAILED"
        db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()
    
@celery_app.task(bind=True, max_retries=3)
def generate_pdf_report(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    
    try:
        job.status = "FINALIZING"
        db.commit()
        
        # 4. Object storage upload via boto3 (S3 / MinIO)
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv('S3_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
        )
        
        bucket_name = "marketai-reports"
        object_key = f"reports/{job_id}.pdf"
        
        # Mock PDF buffer upload
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=b"%PDF-1.4 Mock PDF Document")
        
        job.pdf_object_key = object_key
        job.status = "COMPLETED"
        db.commit()
        
    except Exception as e:
        job.status = "FAILED"
        db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()
