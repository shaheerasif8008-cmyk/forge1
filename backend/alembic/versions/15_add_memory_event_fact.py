"""add memory event and fact tables (correct table names and FKs)

Revision ID: add_mem_event_fact
Revises: c19b207a5444
Create Date: 2025-08-17 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "add_mem_event_fact"
down_revision: Union[str, None] = "c19b207a5444"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Do not hard-require pgvector; embeddings stored as JSONB
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        pass

    # mem_events
    op.create_table(
        "mem_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("employee_id", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="task"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("embedding", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_mem_events_tenant"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_mem_events_employee", ondelete="CASCADE"),
    )
    op.create_index("ix_mem_event_tenant_emp_created", "mem_events", ["tenant_id", "employee_id", "created_at"]) 

    # mem_facts
    op.create_table(
        "mem_facts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("employee_id", sa.String(length=100), nullable=False),
        sa.Column("source_event_id", sa.Integer, nullable=True),
        sa.Column("fact", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("embedding", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_mem_facts_tenant"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_mem_facts_employee", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["mem_events.id"], name="fk_mem_facts_source", ondelete="SET NULL"),
    )
    op.create_index("ix_mem_fact_tenant_emp_created", "mem_facts", ["tenant_id", "employee_id", "created_at"]) 


def downgrade() -> None:
    op.drop_index("ix_mem_fact_tenant_emp_created", table_name="mem_facts")
    try:
        op.drop_constraint("fk_mem_facts_source", "mem_facts", type_="foreignkey")
    except Exception:
        pass
    op.drop_table("mem_facts")
    op.drop_index("ix_mem_event_tenant_emp_created", table_name="mem_events")
    op.drop_table("mem_events")


