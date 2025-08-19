"""add indexes for feature_flags

Revision ID: 10_add_feature_flag_indexes
Revises: 9_unique_employee_tenant_name
Create Date: 2025-08-11 12:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "10_add_feature_flag_indexes"
down_revision = "9_unique_employee_tenant_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "feature_flags" in insp.get_table_names():
        existing = {idx.get("name") for idx in insp.get_indexes("feature_flags")}
        if "ix_feature_flags_tenant" not in existing:
            op.create_index("ix_feature_flags_tenant", "feature_flags", ["tenant_id"], unique=False)
        if "ix_feature_flags_flag" not in existing:
            op.create_index("ix_feature_flags_flag", "feature_flags", ["flag"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "feature_flags" in insp.get_table_names():
        try:
            op.drop_index("ix_feature_flags_flag", table_name="feature_flags")
        except Exception:
            pass
        try:
            op.drop_index("ix_feature_flags_tenant", table_name="feature_flags")
        except Exception:
            pass


