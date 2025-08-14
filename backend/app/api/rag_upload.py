from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.rag.document_loader import DocumentLoader
from ..core.rag.rag_engine import RAGEngine
from ..core.memory.long_term import store_memory
from ..db.session import get_session


router = APIRouter(prefix="/rag", tags=["rag"])


class UploadItem(BaseModel):
    type: str = Field(description="pdf|csv|url|html")
    path: str | None = None
    url: str | None = None
    metadata: dict[str, Any] | None = None


class UploadRequest(BaseModel):
    items: list[UploadItem]


@router.post("/upload")
def upload_docs(
    payload: UploadRequest,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    loader = DocumentLoader()
    specs: list[dict[str, Any]] = []
    for it in payload.items:
        spec: dict[str, Any] = {"type": it.type}
        if it.path:
            spec["path"] = it.path
        if it.url:
            spec["url"] = it.url
        if it.metadata:
            spec["metadata"] = it.metadata
        specs.append(spec)

    docs = loader.load(specs)
    if not docs:
        return {"ingested": 0}

    # Store in LongTermMemory with simple IDs; use index for RAG via query_memory
    for i, d in enumerate(docs):
        content = str(d.get("text") or d.get("content") or "")
        meta = dict(d.get("metadata", {}))
        store_memory(db, memory_id=f"doc_{i}", content=content, metadata=meta, tenant_id=tenant_id)

    # Provide basic RAG indexing ack
    rag = RAGEngine(vector_store=None, retriever=None)  # type: ignore[arg-type]
    # We don't call add_documents here because LongTermMemory already persisted with embeddings.

    return {"ingested": len(docs)}



