"""add RAG tables

Revision ID: 0010_add_rag
Revises: 0002_core_tables
Create Date: 2025-08-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_add_rag"
down_revision = "0002_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_sources",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("uri", sa.String(length=1024), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_rag_sources_key", "rag_sources", ["key"])
    op.create_unique_constraint("uq_rag_source_tenant_key", "rag_sources", ["tenant_id", "key"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"))
    )
    op.create_index("ix_rag_chunks_source_hash", "rag_chunks", ["source_id", "content_hash"], unique=True)
    op.create_index("ix_rag_chunks_source_version", "rag_chunks", ["source_id", "version"])

    op.create_table(
        "rag_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("rag_jobs")
    op.drop_index("ix_rag_chunks_source_version", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_source_hash", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_constraint("uq_rag_source_tenant_key", "rag_sources", type_="unique")
    op.drop_index("ix_rag_sources_key", table_name="rag_sources")
    op.drop_table("rag_sources")


