"""add cost_cents to task_executions

Revision ID: 16_add_cost_cents
Revises: add_mem_event_fact
Create Date: 2025-08-17 23:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "16_add_cost_cents"
down_revision = "add_mem_event_fact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "task_executions" not in inspector.get_table_names():
        return
    cols = {col["name"] for col in inspector.get_columns("task_executions")}
    if "cost_cents" not in cols:
        op.add_column(
            "task_executions",
            sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
        )
        # Drop the server default after backfilling default value for new rows
        with op.batch_alter_table("task_executions") as batch_op:
            batch_op.alter_column("cost_cents", server_default=None)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "task_executions" not in inspector.get_table_names():
        return
    cols = {col["name"] for col in inspector.get_columns("task_executions")}
    if "cost_cents" in cols:
        op.drop_column("task_executions", "cost_cents")


