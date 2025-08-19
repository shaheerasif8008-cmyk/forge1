"""init placeholder

Revision ID: 0a0d0717a24e
Revises: 
Create Date: 2025-08-10 16:07:11.634422

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "0a0d0717a24e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Best-effort: enable pgvector extension, ignore permission errors
    op.execute(
        """
        DO $$
        BEGIN
            BEGIN
                CREATE EXTENSION IF NOT EXISTS vector;
            EXCEPTION WHEN OTHERS THEN
                -- insufficient privilege or other error; proceed without vector
                NULL;
            END;
        END$$;
        """
    )

    # Create long_term_memory table if not exists
    # Use JSONB for embedding to avoid requiring pgvector in non-privileged envs
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "long_term_memory" not in insp.get_table_names():
        op.create_table(
            "long_term_memory",
            sa.Column("id", sa.String(length=100), primary_key=True),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("embedding", JSONB, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Skip vector index by default; can be added by a later optional migration


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ltm_embedding")
    op.drop_table("long_term_memory")
