"""add rollouts table

Revision ID: 4_add_rollouts_table
Revises: 3_add_beta_to_tenants
Create Date: 2025-08-11 00:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4_add_rollouts_table"
down_revision: Union[str, None] = "3_add_beta_to_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rollouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default=sa.text("'off'")),
        sa.Column("percent", sa.Integer(), nullable=True),
        sa.Column("allowlist", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("rollouts")


