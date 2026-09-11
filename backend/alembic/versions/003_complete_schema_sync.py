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

    # 2. Additional columns on evidence
    op.add_column('evidence', sa.Column('canonical_url', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.add_column('evidence', sa.Column('etag', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('status_code', sa.Integer(), nullable=False, server_default='200'))
    op.add_column('evidence', sa.Column('content_type', sa.String(), nullable=False, server_default='text/html'))
    op.add_column('evidence', sa.Column('raw_size', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evidence', sa.Column('snapshot_object_key', sa.String(), nullable=True))
    op.add_column('evidence', sa.Column('source_type', sa.String(), nullable=False, server_default='webpage'))
    op.add_column('evidence', sa.Column('raw_snippet', sa.Text(), nullable=True))

    # 3. Additional columns on claims
    op.add_column('claims', sa.Column('claim_type', sa.String(), nullable=False, server_default='market_insight'))
    op.add_column('claims', sa.Column('value', sa.String(), nullable=True))
    op.add_column('claims', sa.Column('unit', sa.String(), nullable=True))
    op.add_column('claims', sa.Column('confidence', sa.Integer(), nullable=False, server_default='70'))
    op.add_column('claims', sa.Column('extraction_method', sa.String(), nullable=False, server_default='llm_grounded'))
    op.add_column('claims', sa.Column('verification_status', sa.String(), nullable=False, server_default='UNVERIFIED'))
    op.add_column('claims', sa.Column('agreement_ratio', sa.String(), nullable=False, server_default='1/1'))
    op.add_column('claims', sa.Column('verbatim_quote', sa.Text(), nullable=True))

    # 4. claim_sources association table
    op.create_table(
        'claim_sources',
        sa.Column('claim_id', sa.String(), sa.ForeignKey('claims.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('evidence_id', sa.String(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), primary_key=True)
    )
    op.create_index('idx_claim_sources_claim', 'claim_sources', ['claim_id'])
    op.create_index('idx_claim_sources_evidence', 'claim_sources', ['evidence_id'])

    # 5. llm_calls table
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_usd_cost', sa.Numeric(precision=10, scale=6), nullable=False, server_default='0.000000'),
        sa.Column('status', sa.String(), nullable=False, server_default='SUCCESS'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_llm_calls_job', 'llm_calls', ['job_id'])
    op.create_index('idx_llm_calls_org', 'llm_calls', ['org_id'])

    # 6. research_usages table
    op.create_table(
        'research_usages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.String(), sa.ForeignKey('research_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('units_reserved', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('units_consumed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='RESERVED'),
        sa.Column('billing_rule', sa.String(), nullable=False, server_default='standard'),
        sa.Column('reserved_at', sa.DateTime(), nullable=False),
        sa.Column('finalized_at', sa.DateTime(), nullable=True)
    )
    op.create_index('idx_research_usages_org', 'research_usages', ['org_id'])
    op.create_index('idx_research_usages_job', 'research_usages', ['job_id'])

    # 7. research_templates table
    op.create_table(
        'research_templates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=False, server_default='general'),
        sa.Column('mode', sa.String(), nullable=False, server_default='deep'),
        sa.Column('default_prompt_structure', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_templates_org', 'research_templates', ['org_id'])

    # 8. scheduled_research table
    op.create_table(
        'scheduled_research',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('creator_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('product_idea', sa.Text(), nullable=False),
        sa.Column('cron_expression', sa.String(), nullable=False, server_default='0 0 1 * *'),
        sa.Column('mode', sa.String(), nullable=False, server_default='quick'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_scheduled_org', 'scheduled_research', ['org_id'])

    # 9. market_alerts table
    op.create_table(
        'market_alerts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('creator_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_keyword', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False, server_default='competitor_move'),
        sa.Column('threshold_condition', sa.String(), nullable=True),
        sa.Column('notification_channel', sa.String(), nullable=False, server_default='email'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_alerts_org', 'market_alerts', ['org_id'])

def downgrade() -> None:
    op.drop_table('market_alerts')
    op.drop_table('scheduled_research')
    op.drop_table('research_templates')
    op.drop_table('research_usages')
    op.drop_table('llm_calls')
    op.drop_table('claim_sources')
    op.drop_column('subscriptions', 'stripe_price_id')
    op.drop_column('claims', 'verbatim_quote')
    op.drop_column('claims', 'agreement_ratio')
    op.drop_column('claims', 'verification_status')
    op.drop_column('claims', 'extraction_method')
    op.drop_column('claims', 'confidence')
    op.drop_column('claims', 'unit')
    op.drop_column('claims', 'value')
    op.drop_column('claims', 'claim_type')
    op.drop_column('evidence', 'raw_snippet')
    op.drop_column('evidence', 'source_type')
    op.drop_column('evidence', 'snapshot_object_key')
    op.drop_column('evidence', 'raw_size')
    op.drop_column('evidence', 'content_type')
    op.drop_column('evidence', 'status_code')
    op.drop_column('evidence', 'etag')
    op.drop_column('evidence', 'published_at')
    op.drop_column('evidence', 'canonical_url')
