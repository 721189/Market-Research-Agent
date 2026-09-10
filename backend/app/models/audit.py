import uuid
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON, Text
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False) # e.g. research.created, member.invited, billing.updated
    resource_type = Column(String, nullable=False) # research_job, member, api_key, etc.
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_events_org_created", "org_id", "created_at"),
    )
