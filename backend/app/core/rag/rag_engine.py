"""Retrieval-Augmented Generation (RAG) engine abstractions and adapters.

This module defines a minimal, type-safe RAG pipeline that can work with either
LlamaIndex or Haystack components (or both), chosen at runtime. Dependencies on
those frameworks are optional and imported dynamically in adapters.

Core design:
- VectorStore protocol: add() and similarity_search() over simple dict documents
- Retriever protocol: retrieve() for queries
- Reranker protocol: rerank() to reorder retrieved candidates

RAGEngine orchestrates the pipeline:
    add_documents(docs) → store documents (if vector store supports it)
    query(text) → retrieve (via retriever or vector store), optional rerank, return dicts

Document shape used here is a dict with keys:
    {"id": str | None, "content": str, "metadata": dict[str, Any] | None}
The query() method returns dicts with at least: id, content, metadata, score, source
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class VectorStore(Protocol):
    def add(self, documents: list[dict[str, Any]]) -> None:  # pragma: no cover - protocol
        ...

    def similarity_search(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:  # pragma: no cover
        ...


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:  # pragma: no cover
        ...


class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:  # pragma: no cover
        ...


@dataclass
class _Result:
    id: str
    content: str
    metadata: dict[str, Any]
    score: float
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "source": self.source,
        }


class RAGEngine:
    """Configurable RAG engine.

    Provide either a `retriever` or a `vector_store` (or both). If both are present,
    the engine uses the retriever first; otherwise it falls back to the vector store's
    similarity_search. If a `reranker` is present, it will be used to post-process candidates.
    """

    def __init__(
        self,
        *,
        vector_store: VectorStore | None = None,
        retriever: Retriever | None = None,
        reranker: Reranker | None = None,
        default_top_k: int = 5,
    ) -> None:
        if not vector_store and not retriever:
            raise ValueError("RAGEngine requires at least a vector_store or a retriever")

        self.vector_store = vector_store
        self.retriever = retriever
        self.reranker = reranker
        self.default_top_k = max(1, default_top_k)

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """Add documents into the underlying vector store (if provided).

        Each dict should include keys: content (str), optional id (str), optional metadata (dict).
        """
        if not self.vector_store:
            # No-op if vector store is not provided
            return

        normalized: list[dict[str, Any]] = []
        for doc in documents:
            content = str(doc.get("content", "")).strip()
            if not content:
                continue
            normalized.append(
                {
                    "id": str(doc.get("id", "")) or None,
                    "content": content,
                    "metadata": dict(doc.get("metadata", {})),
                }
            )

        if normalized:
            self.vector_store.add(normalized)

    def query(self, query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
        """Retrieve and optionally rerank results.

        Returns a list of dicts: {id, content, metadata, score, source} sorted by best match first.
        """
        k = max(1, int(top_k)) if top_k is not None else self.default_top_k
        candidates: list[dict[str, Any]]

        if self.retriever is not None:
            candidates = self.retriever.retrieve(query, top_k=k)
            source = "retriever"
        elif self.vector_store is not None:
            candidates = self.vector_store.similarity_search(query, top_k=k)
            source = "vector_store"
        else:  # should be unreachable due to constructor check
            raise RuntimeError("No retriever or vector_store configured")

        # Normalize and ensure fields present; default score if missing
        norm_candidates: list[_Result] = []
        for i, c in enumerate(candidates):
            cid = str(c.get("id", f"doc_{i}"))
            content = str(c.get("content", ""))
            meta = dict(c.get("metadata", {}))
            score_val = c.get("score")
            try:
                score = float(score_val) if score_val is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0
            norm_candidates.append(
                _Result(id=cid, content=content, metadata=meta, score=score, source=source)
            )

        # Optional rerank
        if self.reranker is not None and norm_candidates:
            reranked = self.reranker.rerank(query, [r.as_dict() for r in norm_candidates], top_k=k)
            # Re-normalize after reranker
            out: list[_Result] = []
            for i, c in enumerate(reranked):
                cid = str(c.get("id", f"doc_{i}"))
                content = str(c.get("content", ""))
                meta = dict(c.get("metadata", {}))
                score_val = c.get("score")
                try:
                    score = float(score_val) if score_val is not None else 0.0
                except (TypeError, ValueError):
                    score = 0.0
                out.append(
                    _Result(id=cid, content=content, metadata=meta, score=score, source="reranker")
                )
            # Sort by score ascending if scores represent distances; otherwise desc.
            # Here we assume higher is better (similarity); change as needed per reranker semantics.
            out.sort(key=lambda r: r.score, reverse=True)
            return [r.as_dict() for r in out[:k]]

        # Sort initial candidates: assume higher score is better; if scores are distances, caller should
        # map to similarity before passing in. Keep stable order otherwise.
        norm_candidates.sort(key=lambda r: r.score, reverse=True)
        return [r.as_dict() for r in norm_candidates[:k]]


# Optional adapters
class LlamaIndexRetrieverAdapter:
    """Adapter using LlamaIndex to provide a Retriever interface.

    This adapter expects a LlamaIndex index object that exposes `.as_retriever()`
    returning an object with `retrieve(str)` that yields nodes with `.text` and `.metadata`.
    """

    def __init__(self, index: Any, *, top_k: int = 5) -> None:
        self.index = index
        self.top_k = max(1, top_k)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        k = max(1, top_k or self.top_k)
        retriever = self.index.as_retriever(similarity_top_k=k)
        results = retriever.retrieve(query)

        out: list[dict[str, Any]] = []
        for i, r in enumerate(results):
            # LlamaIndex NodeWithScore interface
            text = getattr(r, "text", "") or getattr(getattr(r, "node", None), "text", "") or ""
            meta = getattr(r, "metadata", None)
            if meta is None and getattr(r, "node", None) is not None:
                meta = getattr(r.node, "metadata", {})
            score = float(getattr(r, "score", 0.0))
            out.append(
                {
                    "id": f"llamaindex_{i}",
                    "content": text,
                    "metadata": dict(meta or {}),
                    "score": score,
                }
            )
        return out


class HaystackRetrieverAdapter:
    """Adapter using Haystack to provide a Retriever interface.

    Expects a Haystack retriever with `.retrieve(query, top_k=K)` returning Documents
    with `.content`, `.meta` and optionally `.score`.
    """

    def __init__(self, retriever: Any) -> None:
        self._retriever = retriever

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        docs = self._retriever.retrieve(query, top_k=top_k)
        out: list[dict[str, Any]] = []
        for i, d in enumerate(docs):
            content = getattr(d, "content", "")
            meta = getattr(d, "meta", {})
            score = float(getattr(d, "score", 0.0))
            out.append(
                {
                    "id": str(getattr(d, "id", f"haystack_{i}")),
                    "content": content,
                    "metadata": dict(meta or {}),
                    "score": score,
                }
            )
        return out


class PassthroughReranker:
    """Simple reranker that passes through candidates unchanged.

    Useful as a default or for testing when no reranking model is available.
    """

    def rerank(
        self, query: str, candidates: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        return candidates[: max(1, top_k)]
