"""Long-term memory storage backed by PostgreSQL + pgvector for semantic search."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from ...db.models import LongTermMemory


def _get_embedding(text: str) -> list[float]:
    """Generate or fetch an embedding for the given text.

    NOTE: In production, plug in your embedding provider here (OpenAI, local model, etc.).
    For now, we use a simple deterministic hash-based pseudo-embedding to keep the
    implementation self-contained and testable without external services.
    """
    import hashlib
    import math

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Produce 1536 dims by repeating the digest
    values: list[float] = []
    while len(values) < 1536:
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == 1536:
                break
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def store_memory(
    db: Session, memory_id: str, content: str, metadata: dict[str, Any], *, tenant_id: str | None
) -> None:
    """Create or update a long-term memory entry with vector embedding.

    Args:
        db: SQLAlchemy session
        memory_id: Deterministic identifier for the memory
        content: Raw content/text
        metadata: Arbitrary JSON-serializable metadata
    """
    if tenant_id is None or not str(tenant_id).strip():
        raise ValueError("tenant_id is required for long-term memory operations")
    embedding = _get_embedding(content)
    # Ensure IDs are tenant-namespaced to avoid cross-tenant collisions
    storage_id = f"{tenant_id}:{memory_id}"

    existing: LongTermMemory | None = db.get(LongTermMemory, storage_id)
    if existing is None:
        row = LongTermMemory(
            id=storage_id,
            tenant_id=tenant_id,
            content=content,
            meta=metadata,
            embedding=embedding,
        )
        db.add(row)
    else:
        # Cast to Any to satisfy static typing for SQLAlchemy instrumented attributes
        existing_any = cast(Any, existing)
        existing_any.content = content
        existing_any.meta = metadata
        existing_any.embedding = embedding

    db.commit()


def query_memory(db: Session, query: str, top_k: int = 5, *, tenant_id: str | None) -> list[dict[str, Any]]:
    """Query long-term memory using vector similarity.

    Returns top_k results as a list of dicts with: id, content, metadata, score (cosine distance).
    Lower score is more similar when using cosine distance via pgvector's <=> operator.
    """
    if tenant_id is None or not str(tenant_id).strip():
        raise ValueError("tenant_id is required for long-term memory operations")
    query_embedding = _get_embedding(query)

    # pgvector cosine distance operator <=> when using cosine distance index
    # SQLAlchemy expression: LongTermMemory.embedding.l2_distance(query_embedding) or use func
    distance_expr = LongTermMemory.embedding.cosine_distance(query_embedding)

    stmt: Select[Any] = select(
        LongTermMemory.id,
        LongTermMemory.content,
        LongTermMemory.meta,
        distance_expr.label("score"),
    )

    stmt = stmt.where(and_(LongTermMemory.tenant_id == tenant_id))

    stmt = stmt.order_by(distance_expr.asc()).limit(max(1, top_k))

    rows = db.execute(stmt).all()
    results: list[dict[str, Any]] = []
    for row in rows:
        # Row is a tuple aligned to select columns
        results.append(
            {
                "id": row.id,
                "content": row.content,
                "metadata": row.meta,
                "score": float(row.score),
            }
        )
    return results
