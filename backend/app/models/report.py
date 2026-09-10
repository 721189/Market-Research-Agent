import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, BigInteger
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    object_key = Column(String, nullable=False) # organizations/{org_id}/reports/{report_id}.pdf
    mime_type = Column(String, default="application/pdf", nullable=False)
    size = Column(BigInteger, default=0, nullable=False)
    checksum = Column(String, nullable=True) # SHA-256
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    job = relationship("ResearchJob", back_populates="reports")

    __table_args__ = (
        Index("idx_reports_org_job", "org_id", "job_id"),
    )

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False) # raw_snapshot, evidence_doc, export
    object_key = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
