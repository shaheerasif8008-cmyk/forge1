from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.session import get_session
from ..db.models import RagSource
from ..rag.ingest.stream import register_source, ingest_http, ingest_webhook, ingest_s3
from ..rag.search.hybrid import hybrid_query


router = APIRouter(prefix="/rag", tags=["rag-v2"])


class SourceIn(BaseModel):
    key: str
    type: str = Field(description="http|s3|webhook")
    uri: str | None = None
    meta: dict[str, Any] | None = None


@router.post("/sources")
def post_source(payload: SourceIn, db: Session = Depends(get_session), user=Depends(get_current_user)) -> dict[str, Any]:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    src = register_source(db, tenant_id=tenant_id, key=payload.key, type=payload.type, uri=payload.uri, meta=payload.meta)
    return {"id": src.id, "version": src.version}


class ReindexIn(BaseModel):
    ids: list[str]


@router.post("/reindex")
def reindex(payload: ReindexIn, db: Session = Depends(get_session), user=Depends(get_current_user)) -> dict[str, Any]:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    sources = db.query(RagSource).filter(RagSource.id.in_(payload.ids), RagSource.tenant_id == tenant_id).all()
    queued = 0
    for s in sources:
        if s.type == "http" and s.uri:
            ingest_http(db, source=s, url=s.uri)
            queued += 1
    return {"queued": queued}


class QueryIn(BaseModel):
    q: str
    top_k: int = 5
    alpha: float = 0.5
    sources: list[str] | None = None


@router.post("/query")
def query(payload: QueryIn, db: Session = Depends(get_session), user=Depends(get_current_user)) -> list[dict[str, Any]]:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    return hybrid_query(
        db,
        tenant_id=tenant_id,
        source_ids=payload.sources,
        query=payload.q,
        top_k=payload.top_k,
        alpha=payload.alpha,
    )


