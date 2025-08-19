"""add feature flags table

Revision ID: 2_add_feature_flags
Revises: 0002_core_tables
Create Date: 2025-08-11 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2_add_feature_flags"
down_revision: Union[str, None] = "0002_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("flag", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "flag"),
    )
    op.create_index("ix_feature_flags_tenant", "feature_flags", ["tenant_id"]) 
    op.create_index("ix_feature_flags_flag", "feature_flags", ["flag"]) 


def downgrade() -> None:
    op.drop_index("ix_feature_flags_flag", table_name="feature_flags")
    op.drop_index("ix_feature_flags_tenant", table_name="feature_flags")
    op.drop_table("feature_flags")


