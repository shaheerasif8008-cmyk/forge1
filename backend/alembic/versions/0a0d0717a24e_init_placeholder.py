"""init placeholder

Revision ID: 0a0d0717a24e
Revises: 
Create Date: 2025-08-10 16:07:11.634422

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "0a0d0717a24e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create long_term_memory table
    op.create_table(
        "long_term_memory",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding", Vector(1536)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Optional vector index (cosine)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ltm_embedding ON long_term_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ltm_embedding")
    op.drop_table("long_term_memory")
