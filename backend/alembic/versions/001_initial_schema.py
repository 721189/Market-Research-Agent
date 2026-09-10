"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('firebase_uid', sa.String(), unique=True, nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_superuser', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), unique=True, nullable=False),
        sa.Column('plan', sa.String(), default='free', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Organization Members
    op.create_table(
        'organization_members',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), default='member', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('key_hash', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )

    # Research Jobs
    op.create_table(
        'research_jobs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('creator_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(), default='QUEUED', nullable=False),
        sa.Column('mode', sa.String(), default='deep', nullable=False),
        sa.Column('product_idea', sa.Text(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), default=5, nullable=False),
        sa.Column('progress', sa.Integer(), default=0, nullable=False),
        sa.Column('error_code', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('engine_version', sa.String(), default='2.0.0', nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('pdf_object_key', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    )

    # Research Runs
    op.create_table(
        'research_runs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('status', sa.String(), default='PENDING', nullable=False),
        sa.Column('worker_id', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('run_metadata', sa.JSON(), nullable=True),
    )

    # Research Events
    op.create_table(
        'research_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('progress', sa.Integer(), default=0, nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('level', sa.String(), default='INFO', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Evidence
    op.create_table(
        'evidence',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), default='webpage', nullable=False),
        sa.Column('retrieved_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('content_storage_key', sa.String(), nullable=True),
        sa.Column('authority_score', sa.Integer(), default=50, nullable=False),
        sa.Column('freshness_score', sa.Integer(), default=50, nullable=False),
    )

    # Claims
    op.create_table(
        'claims',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('confidence', sa.Integer(), default=70, nullable=False),
    )

    # Claim Sources (Many-to-Many)
    op.create_table(
        'claim_sources',
        sa.Column('claim_id', sa.String(), sa.ForeignKey('claims.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('evidence_id', sa.String(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), primary_key=True),
    )

    # Reports
    op.create_table(
        'reports',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('object_key', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), default='application/pdf', nullable=False),
        sa.Column('size', sa.BigInteger(), default=0, nullable=False),
        sa.Column('checksum', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Artifacts
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('object_key', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('size', sa.BigInteger(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Usage Events
    op.create_table(
        'usage_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(), default='google-gemini', nullable=False),
        sa.Column('model', sa.String(), default='gemini-1.5-flash', nullable=False),
        sa.Column('input_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('output_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('search_calls', sa.Integer(), default=0, nullable=False),
        sa.Column('duration_ms', sa.Integer(), default=0, nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), default=0.0, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(), default='free', nullable=False),
        sa.Column('status', sa.String(), default='active', nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), default=False, nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Billing Events
    op.create_table(
        'billing_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), default=0, nullable=False),
        sa.Column('currency', sa.String(), default='usd', nullable=False),
        sa.Column('status', sa.String(), default='succeeded', nullable=False),
        sa.Column('stripe_event_id', sa.String(), unique=True, nullable=True),
        sa.Column('event_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('billing_events')
    op.drop_table('subscriptions')
    op.drop_table('usage_events')
    op.drop_table('artifacts')
    op.drop_table('reports')
    op.drop_table('claim_sources')
    op.drop_table('claims')
    op.drop_table('evidence')
    op.drop_table('research_events')
    op.drop_table('research_runs')
    op.drop_table('research_jobs')
    op.drop_table('api_keys')
    op.drop_table('organization_members')
    op.drop_table('organizations')
    op.drop_table('users')
