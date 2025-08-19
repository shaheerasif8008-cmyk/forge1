"""core tables for users, employees, task_executions, audit_logs

Revision ID: 0002_core_tables
Revises: 0001_tenant
Create Date: 2025-08-18 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_core_tables"
down_revision: Union[str, None] = "0001_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("tenant_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_users_tenant", ondelete=None),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    # employees
    op.create_table(
        "employees",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_employees_tenant", ondelete=None),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name="fk_employee_owner_user", ondelete="SET NULL"),
    )
    op.create_index("ix_employees_tenant_created", "employees", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_employees_tenant_name", "employees", ["tenant_id", "name"], unique=False)

    # task_executions (without cost_cents; later migration adds it if needed)
    op.create_table(
        "task_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=True),
        sa.Column("employee_id", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("execution_time", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("task_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_taskexec_tenant", ondelete=None),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_taskexec_employee", ondelete="CASCADE"),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_auditlog_tenant", ondelete=None),
    )
    op.create_index("ix_audit_logs_tenant", "audit_logs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("task_executions")
    op.drop_index("ix_employees_tenant_name", table_name="employees")
    op.drop_index("ix_employees_tenant_created", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")


