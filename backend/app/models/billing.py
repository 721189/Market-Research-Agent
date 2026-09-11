import uuid
import datetime
from typing import Any
try:
    from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Float, Boolean, JSON, Numeric
    from sqlalchemy.orm import relationship
    from backend.app.db.session import Base
except ImportError:
    Base = object # type: ignore
    Column = String = Integer = DateTime = ForeignKey = Index = Float = Boolean = JSON = Numeric = relationship = lambda *a, **kw: None # type: ignore

def generate_uuid():
    return str(uuid.uuid4())

class LLMCall(Base):
    """Canonical structure for tracking every discrete LLM invocation."""
    __tablename__ = "llm_calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    provider = Column(String, default="google-gemini", nullable=False)
    model = Column(String, default="gemini-1.5-flash", nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_code = Column(String, nullable=True)
    estimated_cost = Column(Numeric(10, 6), default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_llm_calls_job", "job_id"),
        Index("idx_llm_calls_org_created", "org_id", "created_at"),
    )

class ResearchUsage(Base):
    """Transactional reservation and finalized quota tracking per research run."""
    __tablename__ = "research_usages"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="RESERVED", nullable=False) # RESERVED, COMMITTED, RELEASED, FAILED
    units_reserved = Column(Integer, default=1, nullable=False)
    units_consumed = Column(Integer, default=0, nullable=False)
    billing_rule = Column(String, default="standard", nullable=False) # standard, waived_on_provider_error, partial_discount
    reserved_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    finalized_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_research_usage_org_status", "org_id", "status"),
        Index("idx_research_usage_job", "job_id"),
    )

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String, default="google-gemini", nullable=False)
    model = Column(String, default="gemini-1.5-flash", nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    search_calls = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    try:
        organization = relationship("Organization", back_populates="usage_events")
    except Exception:
        organization = None

    __table_args__ = (
        Index("idx_usage_events_org_created", "org_id", "created_at"),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String, default="free", nullable=False) # free, starter, pro, enterprise
    status = Column(String, default="active", nullable=False) # active, past_due, canceled, trialing
    current_period_start = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_price_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    try:
        organization = relationship("Organization", back_populates="subscriptions")
    except Exception:
        organization = None

class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    amount_cents = Column(Integer, default=0, nullable=False)
    currency = Column(String, default="usd", nullable=False)
    status = Column(String, default="succeeded", nullable=False)
    stripe_event_id = Column(String, unique=True, index=True, nullable=True)
    event_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
