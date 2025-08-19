"""Long-term memory storage backed by PostgreSQL + pgvector for semantic search."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...db.models import LongTermMemory, MemEvent, MemFact


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


# --------- Helpers for event/fact memory with embeddings ---------

def add_memory_event(db: Session, *, tenant_id: str, employee_id: str, content: str, kind: str = "task", metadata: dict[str, Any] | None = None) -> int:
    if not tenant_id or not employee_id or not content:
        raise ValueError("tenant_id, employee_id and content are required")
    emb = _get_embedding(content)
    row = MemEvent(tenant_id=tenant_id, employee_id=employee_id, kind=kind, content=content, meta=metadata or {}, embedding=emb)
    db.add(row)
    db.commit()
    db.refresh(row)
    return int(row.id)


def add_memory_fact(db: Session, *, tenant_id: str, employee_id: str, fact: str, source_event_id: int | None = None, metadata: dict[str, Any] | None = None) -> int:
    if not tenant_id or not employee_id or not fact:
        raise ValueError("tenant_id, employee_id and fact are required")
    emb = _get_embedding(fact)
    row = MemFact(tenant_id=tenant_id, employee_id=employee_id, source_event_id=source_event_id, fact=fact, meta=metadata or {}, embedding=emb)
    db.add(row)
    db.commit()
    db.refresh(row)
    return int(row.id)


def search_memory(db: Session, *, tenant_id: str, employee_id: str, query: str, top_k: int = 5) -> dict[str, list[dict[str, Any]]]:
    if not tenant_id or not employee_id:
        raise ValueError("tenant_id and employee_id are required")
    if not query:
        ev_rows = db.execute(
            select(MemEvent.id, MemEvent.kind, MemEvent.content, MemEvent.meta).where(
                and_(MemEvent.tenant_id == tenant_id, MemEvent.employee_id == employee_id)
            ).order_by(MemEvent.created_at.desc()).limit(max(1, top_k if top_k else 50))
        ).all()
        fa_rows = db.execute(
            select(MemFact.id, MemFact.fact, MemFact.meta, MemFact.source_event_id).where(
                and_(MemFact.tenant_id == tenant_id, MemFact.employee_id == employee_id)
            ).order_by(MemFact.created_at.desc()).limit(max(1, top_k if top_k else 50))
        ).all()
        return {
            "events": [
                {"id": r.id, "kind": r.kind, "content": r.content, "metadata": r.meta, "score": 0.0} for r in ev_rows
            ],
            "facts": [
                {"id": r.id, "fact": r.fact, "metadata": r.meta, "source_event_id": r.source_event_id, "score": 0.0} for r in fa_rows
            ],
        }
    q_emb = _get_embedding(query)
    # Fetch candidates and score in Python since embeddings are JSONB in tests/local
    ev_rows = db.execute(
        select(MemEvent.id, MemEvent.kind, MemEvent.content, MemEvent.meta, MemEvent.embedding).where(
            and_(MemEvent.tenant_id == tenant_id, MemEvent.employee_id == employee_id)
        ).order_by(MemEvent.created_at.desc()).limit(200)
    ).all()
    fa_rows = db.execute(
        select(MemFact.id, MemFact.fact, MemFact.meta, MemFact.source_event_id, MemFact.embedding).where(
            and_(MemFact.tenant_id == tenant_id, MemFact.employee_id == employee_id)
        ).order_by(MemFact.created_at.desc()).limit(200)
    ).all()

    def _cos(a: list[float] | None, b: list[float]) -> float:
        if not a:
            return 1.0
        # Lower is better to match pgvector <=> cosine distance
        dot = sum((x or 0.0) * (y or 0.0) for x, y in zip(a, b))
        import math
        na = math.sqrt(sum((x or 0.0) * (x or 0.0) for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        cos_sim = dot / (na * nb)
        return 1.0 - cos_sim

    ev_scored = [
        {"id": r.id, "kind": r.kind, "content": r.content, "metadata": r.meta, "score": _cos(r.embedding, q_emb)}
        for r in ev_rows
    ]
    fa_scored = [
        {"id": r.id, "fact": r.fact, "metadata": r.meta, "source_event_id": r.source_event_id, "score": _cos(r.embedding, q_emb)}
        for r in fa_rows
    ]
    ev_scored.sort(key=lambda x: x["score"])  # ascending distance
    fa_scored.sort(key=lambda x: x["score"])  # ascending distance
    return {"events": ev_scored[: max(1, top_k)], "facts": fa_scored[: max(1, top_k)]}

