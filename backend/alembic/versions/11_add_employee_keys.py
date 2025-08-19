"""add employee_keys table

Revision ID: 11_add_employee_keys
Revises: 10_add_feature_flag_indexes
Create Date: 2025-08-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "11_add_employee_keys"
down_revision = "10_add_feature_flag_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "employees" in tables and "employee_keys" not in tables:
        op.create_table(
            "employee_keys",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=100), nullable=False),
            sa.Column("employee_id", sa.String(length=100), nullable=False),
            sa.Column("prefix", sa.String(length=32), nullable=False, unique=True),
            sa.Column("hashed_secret", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
            sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_empkey_tenant"),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_empkey_employee", ondelete="CASCADE"),
        )
    # Ensure index exists
    if "employee_keys" in tables:
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("employee_keys")} 
        if "ix_employee_keys_tenant_employee" not in existing_indexes:
            op.create_index("ix_employee_keys_tenant_employee", "employee_keys", ["tenant_id", "employee_id"], unique=False)


def downgrade() -> None:
    # Best-effort downgrade
    try:
        op.drop_index("ix_employee_keys_tenant_employee", table_name="employee_keys")
    except Exception:
        pass
    try:
        op.drop_table("employee_keys")
    except Exception:
        pass


