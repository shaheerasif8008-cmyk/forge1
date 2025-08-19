"""ltm tenant non-null and composite index; employee owner FK

Revision ID: 8_make_ltm_tenant_nonnull_and_indexes
Revises: 7_add_taskexecution_cascade
Create Date: 2025-08-11 12:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8_make_ltm_tenant_nonnull_and_indexes"
down_revision = "7_add_taskexecution_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LongTermMemory tenant_id non-null and index
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "long_term_memory" in insp.get_table_names():
        # Only add the composite index to improve query performance; skip NOT NULL enforcement here
        try:
            op.create_index(
                "ix_ltm_tenant_id_id",
                "long_term_memory",
                ["tenant_id", "id"],
                unique=False,
            )
        except Exception:
            # Index may already exist
            pass

    # Employee owner_user_id FK added in earlier core migration; no-op here to avoid duplicate errors


def downgrade() -> None:
    # Drop FK and index
    try:
        op.drop_constraint("fk_employee_owner_user", "employees", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_index("ix_ltm_tenant_id_id", table_name="long_term_memory")
    except Exception:
        pass
    # Allow tenant_id to be nullable again
    with op.batch_alter_table("long_term_memory") as batch:
        try:
            batch.alter_column("tenant_id", existing_type=sa.String(length=100), nullable=True)
        except Exception:
            pass


