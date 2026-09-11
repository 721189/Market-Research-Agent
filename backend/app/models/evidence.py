import uuid
import datetime
from typing import Any
try:
    from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Table, Float, Text, Numeric
    from sqlalchemy.orm import relationship
    from backend.app.db.session import Base
except ImportError:
    Base = object # type: ignore
    Column = String = Integer = DateTime = ForeignKey = Index = Table = Float = Text = Numeric = relationship = lambda *a, **kw: None # type: ignore

def generate_uuid():
    return str(uuid.uuid4())

# Association table for Claim <-> Evidence (many-to-many claim sources)
try:
    claim_sources = Table(
        "claim_sources",
        Base.metadata,
        Column("claim_id", String, ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
        Column("evidence_id", String, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
        Index("idx_claim_sources_claim", "claim_id"),
        Index("idx_claim_sources_evidence", "evidence_id")
    )
except Exception:
    claim_sources = None

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    canonical_url = Column(String, nullable=True)
    domain = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    content_hash = Column(String, nullable=True) # SHA-256
    retrieved_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    etag = Column(String, nullable=True)
    status_code = Column(Integer, default=200, nullable=False)
    content_type = Column(String, default="text/html", nullable=False)
    raw_size = Column(Integer, default=0, nullable=False)
    snapshot_object_key = Column(String, nullable=True)
    authority_score = Column(Integer, default=50, nullable=False) # 0 - 100
    freshness_score = Column(Integer, default=50, nullable=False) # 0 - 100
    source_type = Column(String, default="webpage", nullable=False) # official, marketplace, article, financial
    raw_snippet = Column(Text, nullable=True)

    try:
        job = relationship("ResearchJob", back_populates="evidence")
        claims = relationship("Claim", secondary=claim_sources, back_populates="sources")
    except Exception:
        job = None
        claims = None

    __table_args__ = (
        Index("idx_evidence_job_id", "job_id"),
        Index("idx_evidence_domain", "domain"),
        Index("idx_evidence_hash", "content_hash"),
    )

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String, default="market_insight", nullable=False) # market_size, cagr, competitor_pricing, customer_demand, cogs_assumption
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    confidence = Column(Integer, default=70, nullable=False) # 0 - 100
    extraction_method = Column(String, default="llm_grounded", nullable=False) # llm_grounded, cross_validation, heuristic, financial_model
    verification_status = Column(String, default="UNVERIFIED", nullable=False) # CORROBORATED, DISPUTED, SINGLE_SOURCE, UNVERIFIED
    agreement_ratio = Column(String, default="1/1", nullable=False) # e.g. "2/3"
    verbatim_quote = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    try:
        job = relationship("ResearchJob", back_populates="claims")
        sources = relationship("Evidence", secondary=claim_sources, back_populates="claims")
    except Exception:
        job = None
        sources = None

    __table_args__ = (
        Index("idx_claims_job_id", "job_id"),
        Index("idx_claims_type", "claim_type"),
        Index("idx_claims_status", "verification_status"),
    )
