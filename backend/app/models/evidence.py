import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Table, Float, Text
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

# Association table for Claim <-> Evidence (many-to-many claim sources)
claim_sources = Table(
    "claim_sources",
    Base.metadata,
    Column("claim_id", String, ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", String, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_claim_sources_claim", "claim_id"),
    Index("idx_claim_sources_evidence", "evidence_id")
)

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    source_type = Column(String, default="webpage", nullable=False) # official, marketplace, article, financial
    retrieved_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    content_hash = Column(String, nullable=True)
    content_storage_key = Column(String, nullable=True)
    authority_score = Column(Integer, default=50, nullable=False) # 0 - 100
    freshness_score = Column(Integer, default=50, nullable=False) # 0 - 100

    job = relationship("ResearchJob", back_populates="evidence")
    claims = relationship("Claim", secondary=claim_sources, back_populates="sources")

    __table_args__ = (
        Index("idx_evidence_job_id", "job_id"),
    )

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    confidence = Column(Integer, default=70, nullable=False) # 0 - 100

    job = relationship("ResearchJob", back_populates="claims")
    sources = relationship("Evidence", secondary=claim_sources, back_populates="claims")

    __table_args__ = (
        Index("idx_claims_job_id", "job_id"),
    )
