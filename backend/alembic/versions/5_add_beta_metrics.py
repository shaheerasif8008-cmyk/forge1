"""add beta metrics table

Revision ID: 5_add_beta_metrics
Revises: 4_add_rollouts_table
Create Date: 2025-08-11 00:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5_add_beta_metrics"
down_revision: Union[str, None] = "4_add_rollouts_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "beta_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("feature", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
    )
    op.create_index("ix_beta_metrics_tenant", "beta_metrics", ["tenant_id"]) 
    op.create_index("ix_beta_metrics_feature", "beta_metrics", ["feature"]) 
    op.create_index("ix_beta_metrics_status", "beta_metrics", ["status"]) 
    op.create_index("ix_beta_metrics_ts", "beta_metrics", ["ts"]) 


def downgrade() -> None:
    op.drop_index("ix_beta_metrics_ts", table_name="beta_metrics")
    op.drop_index("ix_beta_metrics_status", table_name="beta_metrics")
    op.drop_index("ix_beta_metrics_feature", table_name="beta_metrics")
    op.drop_index("ix_beta_metrics_tenant", table_name="beta_metrics")
    op.drop_table("beta_metrics")


