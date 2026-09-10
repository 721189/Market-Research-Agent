import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

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
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    organization = relationship("Organization", back_populates="usage_events")

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
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="subscriptions")

class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False) # invoice.paid, invoice.payment_failed, customer.subscription.created, etc.
    amount_cents = Column(Integer, default=0, nullable=False)
    currency = Column(String, default="usd", nullable=False)
    status = Column(String, default="succeeded", nullable=False)
    stripe_event_id = Column(String, unique=True, index=True, nullable=True)
    event_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
