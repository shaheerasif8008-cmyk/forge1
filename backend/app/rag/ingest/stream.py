from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import httpx
from redis import Redis
from sqlalchemy.orm import Session
from sqlalchemy import text as _sqltext

from ...core.config import settings
from ...db.models import RagSource, RagChunk, RagJob
from ...db.session import SessionLocal


QUEUE_KEY = "rag:embed:queue"


def sha256_hexdigest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class IngestItem:
    content: str
    meta: dict[str, Any]


def register_source(db: Session, *, tenant_id: str, key: str, type: str, uri: str | None, meta: dict | None) -> RagSource:
    # Tables managed by Alembic
    src = db.query(RagSource).filter(RagSource.tenant_id == tenant_id, RagSource.key == key).one_or_none()
    if src is None:
        src = RagSource(id=f"src_{tenant_id}_{key}", tenant_id=tenant_id, key=key, type=type, uri=uri, meta=meta or {}, version=1)
        db.add(src)
    else:
        src.uri = uri
        src.meta = meta or {}
        src.version = int(src.version or 1) + 1
    db.commit()
    return src


def _enqueue_embed(task: dict[str, Any]) -> None:
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    r.lpush(QUEUE_KEY, json.dumps(task))


def ingest_http(db: Session, *, source: RagSource, url: str) -> dict[str, Any]:
    resp = httpx.get(url, timeout=20.0)
    resp.raise_for_status()
    text = resp.text
    return _ingest_text(db, source=source, text=text, meta={"source": url})


def ingest_webhook(db: Session, *, source: RagSource, payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    return _ingest_text(db, source=source, text=text, meta={"source": "webhook"})


def ingest_s3(db: Session, *, source: RagSource, content: str, path: str) -> dict[str, Any]:
    return _ingest_text(db, source=source, text=content, meta={"source": path})


def _chunk_text(text: str, *, max_len: int = 1400, overlap: int = 100) -> list[str]:
    t = text.strip()
    if not t:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(t):
        end = min(len(t), i + max_len)
        chunks.append(t[i:end])
        if end == len(t):
            break
        i = end - overlap
        if i < 0:
            i = 0
    return chunks


def _ensure_tables(db: Session) -> None:
    try:
        # Tables managed by Alembic
        pass
    except Exception:
        pass


def _ingest_text(db: Session, *, source: RagSource, text: str, meta: dict[str, Any]) -> dict[str, Any]:
    _ensure_tables(db)
    chunks = _chunk_text(text)
    added = 0
    skipped = 0
    for ch in chunks:
        h = sha256_hexdigest(ch)
        exists = (
            db.query(RagChunk)
            .filter(RagChunk.source_id == source.id, RagChunk.content_hash == h)
            .one_or_none()
        )
        if exists:
            skipped += 1
            continue
        row = RagChunk(
            id=f"chk_{h[:16]}",
            source_id=source.id,
            content_hash=h,
            content=ch,
            meta=meta,
            version=source.version,
        )
        db.add(row)
        added += 1
        _enqueue_embed({"chunk_id": row.id, "tenant_id": source.tenant_id})
    db.commit()
    # Create a job record
    try:
        # Tables managed by Alembic
        pass
    except Exception:
        pass
    job = RagJob(tenant_id=source.tenant_id, source_id=source.id, status="queued", error=None)
    db.add(job)
    db.commit()
    return {"added": added, "skipped": skipped, "job_id": job.id}


