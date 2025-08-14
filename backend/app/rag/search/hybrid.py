from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ...db.models import RagChunk


def hybrid_query(
    db: Session,
    *,
    tenant_id: str,
    source_ids: list[str] | None,
    query: str,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict[str, Any]]:
    """Hybrid BM25 + pgvector ANN ranking with tunable alpha.

    We approximate BM25 using Postgres full-text search ranking (ts_rank_cd) by
    tokenizing content via to_tsvector. Vector similarity uses cosine distance.
    Final score = alpha * bm25_norm + (1 - alpha) * (1 - cosine_distance_norm).
    """

    # Text search
    ts_query = func.plainto_tsquery("english", query)
    tsv = func.to_tsvector("english", RagChunk.content)
    rank = func.ts_rank_cd(tsv, ts_query)

    # Vector similarity (lower is closer); normalize roughly via 1 - d
    # We store embedding as JSON; we'll compute similarity client-side after fetching rows

    stmt = select(
        RagChunk.id,
        RagChunk.source_id,
        RagChunk.content,
        RagChunk.meta,
        rank.label("bm25"),
        RagChunk.embedding,
    )
    if source_ids:
        stmt = stmt.where(RagChunk.source_id.in_(source_ids))
    stmt = stmt.order_by(rank.desc()).limit(max(50, top_k * 4))
    rows = db.execute(stmt).all()

    # Compute cosine distance client-side between query embedding and row embedding
    from ...core.memory.long_term import _get_embedding as _emb

    qv = _emb(query)
    def cosine(u: list[float], v: list[float]) -> float:
        num = sum(a * b for a, b in zip(u, v))
        # vectors are unit-norm in _emb; so denom = 1
        return num

    out: list[dict[str, Any]] = []
    bm_max = max((float(r.bm25) for r in rows), default=1.0) or 1.0
    for r in rows:
        emb = list(r.embedding or [])
        sim = cosine(qv, emb) if emb else 0.0  # similarity in [-1,1]
        sim01 = (sim + 1.0) / 2.0  # map to [0,1]
        bm = float(r.bm25 or 0.0) / bm_max
        score = alpha * bm + (1 - alpha) * sim01
        out.append({
            "id": r.id,
            "source_id": r.source_id,
            "content": r.content,
            "meta": r.meta,
            "score": score,
            "bm25": float(r.bm25 or 0.0),
            "sim": sim01,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[: top_k]


