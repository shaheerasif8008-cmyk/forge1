"""add beta column to tenants

Revision ID: 3_add_beta_to_tenants
Revises: 2_add_feature_flags
Create Date: 2025-08-11 00:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3_add_beta_to_tenants"
down_revision: Union[str, None] = "2_add_feature_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("beta", sa.Boolean(), server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("tenants", "beta")


