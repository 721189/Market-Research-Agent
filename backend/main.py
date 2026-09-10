from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from .database import get_db, engine
from . import models, tasks
from pydantic import BaseModel
from typing import Optional
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MarketAI API", version="1.0")

class ResearchRequest(BaseModel):
    orgId: str
    product_idea: str
    mode: str = "deep"
    idempotencyKey: Optional[str] = None

@app.post("/api/v1/research")
def start_research(req: ResearchRequest, request: Request, db: Session = Depends(get_db)):
    # Security: Multi-layer rate limit check, Auth validation would happen via dependencies
    
    # 7. Idempotency: Duplicate job detection
    if req.idempotencyKey:
        existing = db.query(models.ResearchJob).filter(
            models.ResearchJob.org_id == req.orgId,
            models.ResearchJob.idempotency_key == req.idempotencyKey
        ).first()
        if existing:
            return {"task_id": existing.id}
            
    # 1. Database Creation
    job = models.ResearchJob(
        org_id=req.orgId, 
        product_idea=req.product_idea, 
        mode=req.mode,
        status="QUEUED",
        idempotency_key=req.idempotencyKey
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # 8. Worker Fleet: Route to specific queue
    queue_name = f"research.{req.mode}"
    tasks.execute_research_job.apply_async(args=[job.id], queue=queue_name)
    
    return {"task_id": job.id}

@app.get("/api/v1/research/{task_id}")
def get_research_status(task_id: str, db: Session = Depends(get_db)):
    job = db.query(models.ResearchJob).filter(models.ResearchJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    
    return {
        "task_id": job.id,
        "status": job.status,
        "result": job.result
    }

@app.get("/health/live")
def health_live():
    return {"status": "ok"}
