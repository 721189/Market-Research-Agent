from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import declarative_base
import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String)
    plan = Column(String, default="free")

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"))
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String)

class ResearchJob(Base):
    __tablename__ = "research_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"))
    status = Column(String, default="QUEUED") 
    product_idea = Column(String)
    mode = Column(String)
    result = Column(JSON, nullable=True)
    pdf_object_key = Column(String, nullable=True)
    idempotency_key = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id"))
    url = Column(String)
    content_hash = Column(String)
    authority_score = Column(Integer)
    
class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("research_jobs.id"))
    text = Column(String)
    confidence = Column(Integer)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"))
    job_id = Column(String, ForeignKey("research_jobs.id"))
    tokens = Column(Integer)
    estimated_cost_usd = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
