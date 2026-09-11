import pytest
from backend.app.models.auth import Organization, User, ApiKey
from backend.app.models.research import ResearchJob, ResearchRun, ResearchUsage
from backend.app.models.evidence import Evidence, Claim
from backend.app.services.entitlement import entitlement_service
import datetime
import uuid

def test_golden_path_lifecycle(db_session):
    # This test assumes a pytest fixture `db_session` provides a real DB connection.
    # In CI, we run this against a real Postgres container.
    
    # 1. Create Organization & User
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    org = Organization(id=org_id, name="Test Org", slug=f"test-{org_id}", plan="pro", created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
    db_session.add(org)
    
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    user = User(id=user_id, email="test@marketai.app", full_name="Test User", created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
    db_session.add(user)
    db_session.commit()
    
    # 2. Create Research Request & Reserve Quota
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job = ResearchJob(id=job_id, org_id=org_id, creator_id=user_id, status="QUEUED", mode="quick", product_idea="Golden Path Test", created_at=datetime.datetime.utcnow())
    db_session.add(job)
    
    usage = ResearchUsage(id=f"use_{uuid.uuid4().hex[:8]}", org_id=org_id, job_id=job_id, status="RESERVED", created_at=datetime.datetime.utcnow())
    db_session.add(usage)
    db_session.commit()
    
    # 3. Research Worker Simulator (creates evidence)
    job.status = "RESEARCHING"
    ev = Evidence(id=f"ev_{uuid.uuid4().hex[:8]}", job_id=job_id, url="https://example.com", domain="example.com", retrieved_at=datetime.datetime.utcnow())
    db_session.add(ev)
    db_session.commit()
    
    # 4. Analysis Worker Simulator (creates claims & completes)
    job.status = "ANALYZING"
    claim = Claim(id=f"cl_{uuid.uuid4().hex[:8]}", job_id=job_id, claim_text="Market is growing", extraction_method="llm")
    db_session.add(claim)
    
    job.status = "COMPLETED"
    db_session.commit()
    
    # 5. Quota Finalization (should be idempotent)
    entitlement_service.finalize_usage(db_session, job_id, units=1)
    db_session.refresh(usage)
    assert usage.status == "COMMITTED"
    
    # Second call should be a no-op
    entitlement_service.finalize_usage(db_session, job_id, units=2)
    db_session.refresh(usage)
    assert usage.units_consumed == 1 # Still 1
