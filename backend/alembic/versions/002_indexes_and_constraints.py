"""Indexes and constraints

Revision ID: 002_indexes_and_constraints
Revises: 001_initial_schema
Create Date: 2026-09-10 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_indexes_and_constraints'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 2.3 Unique constraints
    op.create_unique_constraint('uq_org_idempotency', 'research_jobs', ['org_id', 'idempotency_key'])
    op.create_unique_constraint('uq_org_user', 'organization_members', ['org_id', 'user_id'])

    # 2.4 Performance indexes
    op.create_index('idx_research_jobs_org_created', 'research_jobs', ['org_id', 'created_at'])
    op.create_index('idx_research_jobs_status_created', 'research_jobs', ['status', 'created_at'])
    op.create_index('idx_research_jobs_org_status', 'research_jobs', ['org_id', 'status'])
    op.create_index('idx_evidence_job_id', 'evidence', ['job_id'])
    op.create_index('idx_claims_job_id', 'claims', ['job_id'])
    op.create_index('idx_usage_events_org_created', 'usage_events', ['org_id', 'created_at'])
    op.create_index('idx_org_members_user_id', 'organization_members', ['user_id'])
    op.create_index('idx_org_members_org_id', 'organization_members', ['org_id'])
    op.create_index('idx_reports_org_job', 'reports', ['org_id', 'job_id'])
    op.create_index('idx_audit_events_org_created', 'audit_events', ['org_id', 'created_at'])

def downgrade() -> None:
    op.drop_index('idx_audit_events_org_created', table_name='audit_events')
    op.drop_index('idx_reports_org_job', table_name='reports')
    op.drop_index('idx_org_members_org_id', table_name='organization_members')
    op.drop_index('idx_org_members_user_id', table_name='organization_members')
    op.drop_index('idx_usage_events_org_created', table_name='usage_events')
    op.drop_index('idx_claims_job_id', table_name='claims')
    op.drop_index('idx_evidence_job_id', table_name='evidence')
    op.drop_index('idx_research_jobs_org_status', table_name='research_jobs')
    op.drop_index('idx_research_jobs_status_created', table_name='research_jobs')
    op.drop_index('idx_research_jobs_org_created', table_name='research_jobs')

    op.drop_constraint('uq_org_user', 'organization_members', type_='unique')
    op.drop_constraint('uq_org_idempotency', 'research_jobs', type_='unique')
