"""tracing and observability tables

Revision ID: 14_tracing_observability
Revises: 13_self_tuning_models
Create Date: 2025-08-14 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '14_tracing_observability'
down_revision: Union[str, None] = '13_self_tuning_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trace_spans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('trace_id', sa.String(length=64), nullable=False, index=True),
        sa.Column('span_id', sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column('parent_span_id', sa.String(length=64), nullable=True, index=True),
        sa.Column('tenant_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('employee_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('span_type', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index('ix_trace_spans_trace_parent', 'trace_spans', ['trace_id', 'parent_span_id'])
    op.create_index('ix_trace_spans_tenant_trace', 'trace_spans', ['tenant_id', 'trace_id'])

    # run_failures table if missing
    op.create_table(
        'run_failures',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_execution_id', sa.Integer(), nullable=True, index=True),
        sa.Column('tenant_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('employee_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # data_lifecycle_policies table if missing
    op.create_table(
        'data_lifecycle_policies',
        sa.Column('tenant_id', sa.String(length=100), primary_key=True),
        sa.Column('chat_ttl_days', sa.Integer(), nullable=True),
        sa.Column('tool_io_ttl_days', sa.Integer(), nullable=True),
        sa.Column('pii_redaction_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('data_lifecycle_policies')
    op.drop_table('run_failures')
    op.drop_index('ix_trace_spans_tenant_trace', table_name='trace_spans')
    op.drop_index('ix_trace_spans_trace_parent', table_name='trace_spans')
    op.drop_table('trace_spans')


