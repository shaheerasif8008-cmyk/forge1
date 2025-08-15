"""self-tuning models and columns

Revision ID: 13_self_tuning_models
Revises: c19b207a5444
Create Date: 2025-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '13_self_tuning_models'
down_revision: Union[str, None] = 'c19b207a5444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # EmployeeVersions table
    op.create_table(
        'employee_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('parent_version_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_version_id'], ['employee_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_employee_versions_emp_status', 'employee_versions', ['employee_id', 'status'], unique=False)
    op.create_unique_constraint('uq_employee_version', 'employee_versions', ['employee_id', 'version'])

    # PerformanceSnapshots table
    op.create_table(
        'performance_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.String(length=100), nullable=False),
        sa.Column('employee_version_id', sa.Integer(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('avg_cost_cents', sa.Float(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_version_id'], ['employee_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_perf_snap_emp_version', 'performance_snapshots', ['employee_id', 'employee_version_id'], unique=False)

    # Add active_version_id to employees
    op.add_column('employees', sa.Column('active_version_id', sa.Integer(), nullable=True))
    op.create_index('ix_employees_active_version', 'employees', ['active_version_id'], unique=False)
    op.create_foreign_key('fk_employees_active_version', 'employees', 'employee_versions', ['active_version_id'], ['id'], ondelete='SET NULL')

    # Add cost_cents to task_executions
    op.add_column('task_executions', sa.Column('cost_cents', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('task_executions', 'cost_cents')
    op.drop_constraint('fk_employees_active_version', 'employees', type_='foreignkey')
    op.drop_index('ix_employees_active_version', table_name='employees')
    op.drop_column('employees', 'active_version_id')
    op.drop_index('ix_perf_snap_emp_version', table_name='performance_snapshots')
    op.drop_table('performance_snapshots')
    op.drop_constraint('uq_employee_version', 'employee_versions', type_='unique')
    op.drop_index('ix_employee_versions_emp_status', table_name='employee_versions')
    op.drop_table('employee_versions')


