"""add webhook endpoints and deliveries tables

Revision ID: 19_add_webhook_tables
Revises: 18_add_supervisor_policy_controls
Create Date: 2025-08-17 23:25:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "19_add_webhook_tables"
down_revision = "18_add_supervisor_policy_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("event_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_tenant_active", "webhook_endpoints", ["tenant_id", "active"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("endpoint_id", sa.Integer(), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("message_id", sa.String(length=50), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signature", sa.String(length=200), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_delivery_endpoint_message", "webhook_deliveries", ["endpoint_id", "message_id"])
    op.create_index("ix_webhook_deliveries_tenant_status", "webhook_deliveries", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_tenant_status", table_name="webhook_deliveries")
    op.drop_constraint("uq_delivery_endpoint_message", "webhook_deliveries", type_="unique")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_webhook_tenant_active", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")


