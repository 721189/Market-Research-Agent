"""Complete schema sync for all models

Revision ID: 003_complete_schema_sync
Revises: 002_indexes_and_constraints
Create Date: 2026-09-10 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_complete_schema_sync'
down_revision = '002_indexes_and_constraints'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. New column on subscriptions
    op.add_column('subscriptions', sa.Column('stripe_price_id', sa.String(), nullable=True))

    # 2. Additional columns on organizations & api_keys
    op.add_column('organizations', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('api_keys', sa.Column('key_prefix', sa.String(), nullable=False, server_default='mk_live_'))
    op.add_column('api_keys', sa.Column('role', sa.String(), nullable=False, server_default='member'))
    op.add_column('api_keys', sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('api_keys', sa.Column('last_used_at', sa.DateTime(), nullable=True))

    # 3. Additional columns on evidence
    op.add_column('evidence', sa.Column('canonical_url', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('etag', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('status_code', sa.Integer(), nullable=False, server_default='200'))
    op.add_column('evidence', sa.Column('content_type', sa.String(), nullable=False, server_default='text/html'))
    op.add_column('evidence', sa.Column('raw_size', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evidence', sa.Column('snapshot_object_key', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('raw_snippet', sa.Text(), nullable=True))

    # 4. Additional columns on claims
    op.add_column('claims', sa.Column('claim_type', sa.String(), nullable=False, server_default='market_insight'))
    op.add_column('claims', sa.Column('extraction_method', sa.String(), nullable=False, server_default='llm_grounded'))
    op.add_column('claims', sa.Column('verification_status', sa.String(), nullable=False, server_default='UNVERIFIED'))
    op.add_column('claims', sa.Column('agreement_ratio', sa.String(), nullable=False, server_default='1/1'))
    op.add_column('claims', sa.Column('verbatim_quote', sa.Text(), nullable=True))

    # 6. llm_calls table (exact match to LLMCall ORM)
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('provider', sa.String(), nullable=False, server_default='google-gemini'),
        sa.Column('model', sa.String(), nullable=False, server_default='gemini-1.5-flash'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_code', sa.String(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=6), nullable=False, server_default='0.000000'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_llm_calls_job', 'llm_calls', ['job_id'])
    op.create_index('idx_llm_calls_org_created', 'llm_calls', ['org_id', 'created_at'])

    # 7. research_usages table (exact match to ResearchUsage ORM)
    op.create_table(
        'research_usages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='RESERVED'),
        sa.Column('units_reserved', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('units_consumed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('billing_rule', sa.String(), nullable=False, server_default='standard'),
        sa.Column('reserved_at', sa.DateTime(), nullable=False),
        sa.Column('finalized_at', sa.DateTime(), nullable=True)
    )
    op.create_index('idx_research_usage_org_status', 'research_usages', ['org_id', 'status'])
    op.create_index('idx_research_usage_job', 'research_usages', ['job_id'])

    # 8. research_templates table (exact match to ResearchTemplate ORM)
    op.create_table(
        'research_templates',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=32), nullable=True, server_default='quick'),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('default_parameters', sa.JSON(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('idx_templates_id', 'research_templates', ['id'])

    # 9. scheduled_research table (exact match to ScheduledResearch ORM)
    op.create_table(
        'scheduled_research',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('creator_id', sa.String(length=64), nullable=False),
        sa.Column('product_idea', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(length=32), nullable=True, server_default='quick'),
        sa.Column('cron_schedule', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('idx_scheduled_id', 'scheduled_research', ['id'])
    op.create_index('idx_scheduled_org', 'scheduled_research', ['org_id'])

    # 10. market_alerts table (exact match to MarketAlert ORM)
    op.create_table(
        'market_alerts',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('product_idea', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=True, server_default='INFO'),
        sa.Column('headline', sa.String(length=255), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('idx_alerts_id', 'market_alerts', ['id'])
    op.create_index('idx_alerts_org', 'market_alerts', ['org_id'])

def downgrade() -> None:
    op.drop_table('market_alerts')
    op.drop_table('scheduled_research')
    op.drop_table('research_templates')
    op.drop_table('research_usages')
    op.drop_table('llm_calls')
    op.drop_column('claims', 'verbatim_quote')
    op.drop_column('claims', 'agreement_ratio')
    op.drop_column('claims', 'verification_status')
    op.drop_column('claims', 'extraction_method')
    op.drop_column('claims', 'claim_type')
    op.drop_column('evidence', 'raw_snippet')
    op.drop_column('evidence', 'snapshot_object_key')
    op.drop_column('evidence', 'raw_size')
    op.drop_column('evidence', 'content_type')
    op.drop_column('evidence', 'status_code')
    op.drop_column('evidence', 'etag')
    op.drop_column('evidence', 'canonical_url')
    op.drop_column('api_keys', 'last_used_at')
    op.drop_column('api_keys', 'is_revoked')
    op.drop_column('api_keys', 'role')
    op.drop_column('api_keys', 'key_prefix')
    op.drop_column('organizations', 'status')
    op.drop_column('subscriptions', 'stripe_price_id')
