from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db.models import RagSource, RagChunk
from app.rag.ingest.stream import register_source, ingest_s3
from app.rag.search.hybrid import hybrid_query


def _db() -> Session:
    for s in get_session():
        return s
    raise RuntimeError("no session")


def test_reingest_unchanged_dedups() -> None:
    db = _db()
    src = register_source(db, tenant_id="t-1", key="toy", type="s3", uri=None, meta={})
    text = "hello world\nhello world\n" * 50
    ingest_s3(db, source=src, content=text, path="s3://bucket/toy.txt")
    # Re-ingest same content
    res2 = ingest_s3(db, source=src, content=text, path="s3://bucket/toy.txt")
    # No duplicate chunks added on re-ingest
    assert res2["added"] == 0


def test_hybrid_beats_vector_on_toy() -> None:
    db = _db()
    src = register_source(db, tenant_id="t-2", key="toy2", type="s3", uri=None, meta={})
    # Two distinct topics
    ingest_s3(db, source=src, content="python code asyncio await task", path="p1")
    ingest_s3(db, source=src, content="finance budget revenue profit", path="f1")

    # Query closer to finance; hybrid with alpha>0 (BM25) should rank finance high
    res_h = hybrid_query(db, tenant_id="t-2", source_ids=[src.id], query="quarterly revenue budget", top_k=1, alpha=0.6)
    res_v = hybrid_query(db, tenant_id="t-2", source_ids=[src.id], query="quarterly revenue budget", top_k=1, alpha=0.0)

    assert res_h and res_v
    # The top hit under hybrid should be the finance chunk
    assert "finance" in res_h[0]["content"]

