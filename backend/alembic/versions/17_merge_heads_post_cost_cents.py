"""merge heads after cost_cents

Revision ID: 17_merge_heads_post_cost_cents
Revises: b4191b89308c, 16_add_cost_cents
Create Date: 2025-08-17 23:05:00
"""

from __future__ import annotations

# This is a merge migration; no operations required
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "17_merge_heads_post_cost_cents"
down_revision = ("b4191b89308c", "16_add_cost_cents")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


