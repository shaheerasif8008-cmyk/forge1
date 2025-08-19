"""add supervisor policy control flags

Revision ID: 18_add_supervisor_policy_controls
Revises: 17_merge_heads_post_cost_cents
Create Date: 2025-08-17 23:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "18_add_supervisor_policy_controls"
down_revision = "17_merge_heads_post_cost_cents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "supervisor_policy" not in insp.get_table_names():
        op.create_table(
            "supervisor_policy",
            sa.Column("tenant_id", sa.String(length=100), primary_key=True),
            sa.Column("budget_per_request_cents", sa.Integer(), nullable=True),
            sa.Column("budget_per_day_cents", sa.Integer(), nullable=True),
            sa.Column("require_human_for", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("deny_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("pii_strict", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("ghost_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("pause_high_impact", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
    else:
        cols = {c["name"] for c in insp.get_columns("supervisor_policy")}
        if "ghost_mode" not in cols:
            op.add_column("supervisor_policy", sa.Column("ghost_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        if "pause_high_impact" not in cols:
            op.add_column("supervisor_policy", sa.Column("pause_high_impact", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "supervisor_policy" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("supervisor_policy")}
        if "pause_high_impact" in cols:
            op.drop_column("supervisor_policy", "pause_high_impact")
        if "ghost_mode" in cols:
            op.drop_column("supervisor_policy", "ghost_mode")


