import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class ResearchTemplate(Base):
    __tablename__ = "research_templates"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False) # saas, d2c, b2b_marketplace, dev_tools
    mode = Column(String(32), default="quick")
    prompt_template = Column(Text, nullable=False)
    default_parameters = Column(JSON, default=dict)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ScheduledResearch(Base):
    __tablename__ = "scheduled_research"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), nullable=False, index=True)
    creator_id = Column(String(64), nullable=False)
    product_idea = Column(Text, nullable=False)
    mode = Column(String(32), default="quick")
    cron_schedule = Column(String(64), nullable=False) # e.g. "0 9 * * 1" (Weekly Monday 9AM)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MarketAlert(Base):
    __tablename__ = "market_alerts"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), nullable=False, index=True)
    product_idea = Column(String(255), nullable=False)
    alert_type = Column(String(64), nullable=False) # pricing_change, new_competitor, cagr_revision
    severity = Column(String(32), default="INFO")
    headline = Column(String(255), nullable=False)
    details = Column(JSON, default=dict)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
