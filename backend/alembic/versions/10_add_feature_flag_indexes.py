"""add indexes for feature_flags

Revision ID: 10_add_feature_flag_indexes
Revises: 9_unique_employee_tenant_name
Create Date: 2025-08-11 12:20:00
"""

from __future__ import annotations

from alembic import op


revision = "10_add_feature_flag_indexes"
down_revision = "9_unique_employee_tenant_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_feature_flags_tenant", "feature_flags", ["tenant_id"], unique=False)
    op.create_index("ix_feature_flags_flag", "feature_flags", ["flag"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feature_flags_flag", table_name="feature_flags")
    op.drop_index("ix_feature_flags_tenant", table_name="feature_flags")


