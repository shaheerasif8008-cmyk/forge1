"""add promotion audit table

Revision ID: 6_add_promotion_audit
Revises: 5_add_beta_metrics
Create Date: 2025-08-11 00:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6_add_promotion_audit"
down_revision: Union[str, None] = "5_add_beta_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_promotions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("feature", sa.String(length=200), nullable=False),
        sa.Column("tenant_ids", sa.JSON(), nullable=False),
        sa.Column("performed_by", sa.String(length=100), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_promotions")


