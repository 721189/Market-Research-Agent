import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint, JSON, Text
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    creator_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, default="QUEUED", nullable=False) # QUEUED, RESEARCHING, ANALYZING, GENERATING_REPORT, COMPLETED, RETRYING, FAILED, CANCELLING, CANCELLED
    mode = Column(String, default="deep", nullable=False) # quick, deep, batch
    product_idea = Column(Text, nullable=False)
    idempotency_key = Column(String, nullable=True, index=True)
    priority = Column(Integer, default=5, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    engine_version = Column(String, default="2.0.0", nullable=False)
    result = Column(JSON, nullable=True)
    pdf_object_key = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="jobs")
    runs = relationship("ResearchRun", back_populates="job", cascade="all, delete-orphan")
    events = relationship("ResearchEvent", back_populates="job", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="job", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="job", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_org_idempotency"),
        Index("idx_research_jobs_org_created", "org_id", "created_at"),
        Index("idx_research_jobs_status_created", "status", "created_at"),
        Index("idx_research_jobs_org_status", "org_id", "status"),
    )

class ResearchRun(Base):
    __tablename__ = "research_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String, nullable=False) # research, analysis, report
    status = Column(String, default="PENDING", nullable=False)
    worker_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    run_metadata = Column(JSON, nullable=True)

    job = relationship("ResearchJob", back_populates="runs")

class ResearchEvent(Base):
    __tablename__ = "research_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    message = Column(String, nullable=False)
    level = Column(String, default="INFO", nullable=False) # INFO, WARN, ERROR
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    job = relationship("ResearchJob", back_populates="events")
